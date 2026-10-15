"""Cross-instance serialization and durable potion state (one ledger per host)."""

import copy
import fcntl
import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from inventory_tracking.models import Actor, PotionType, SessionIdentity
from inventory_tracking.reports import publish


Timestamp = Annotated[float, Field(ge=0, allow_inf_nan=False)]
CoreIdentity = tuple[int, str, int]
LEDGER_NAME = 'potions.json'
# Where `make osd` keeps it: the directory of its sessions (osd/__main__.py `--output`'s default, one level up from a
# session), for a reader in another process (`PotionLedger.given_at`)
OSD_LEDGER = Path(__file__).resolve().parents[1] / 'runs' / 'osd'
LOCK_NAME = 'potions.lock'
# Before version 2 the lock file was also the store for one shared timestamp.
LEGACY_LOCK_NAME = 'merc-input.lock'
# A claim by the macro's drinker (`PotionLedger.claim`) waits this long for the lock the healer holds while it reads
# a sample (a few ms) or presses a key (tens of ms); still held after it, the healer is delivering and has the blow.
CLAIM_WAIT = 0.03
CLAIM_POLL = 0.005


def cooldown_key(actor: Actor, potion: PotionType) -> str:
    return f'{actor}:{potion}'


COOLDOWN_KEYS = frozenset(cooldown_key(actor, potion) for actor in Actor for potion in PotionType)


class Record(BaseModel):
    """Persisted policy is strictly typed so a malformed file cannot weaken an input guard."""

    model_config = ConfigDict(strict=True, extra='forbid', validate_assignment=True)


class PendingReservation(Record):
    item_id: int
    sent_at: Timestamp


class ActorRecord(Record):
    session: SessionIdentity
    pending: PendingReservation | None = None
    # Permanent for this session: an input error left key state unknown.
    suspended: bool = False
    # Unconsumed potions in a row; each one defers the next attempt to retry_at, enough of them pause until
    # suspended_until. Both clear on their own.
    misses: Annotated[int, Field(ge=0)] = 0
    retry_at: Timestamp | None = None
    suspended_until: Timestamp | None = None


class LastDelivery(Record):
    session: CoreIdentity
    at: Timestamp


class LedgerData(Record):
    version: Literal[2]
    boot: str
    cooldowns: dict[str, Timestamp]
    actors: dict[Actor, ActorRecord]
    last_delivery: LastDelivery | None

    @field_validator('cooldowns', mode='after')
    @classmethod
    def _known_cooldown_keys(cls, values: dict[str, float]) -> dict[str, float]:
        if set(values) - COOLDOWN_KEYS:
            raise ValueError('Invalid potion cooldown key')
        return values

    @classmethod
    def empty(cls, boot: str) -> Self:
        return cls(version=2, boot=boot, cooldowns={}, actors={}, last_delivery=None)


def migrate(raw: dict[str, Any], boot: str) -> str:
    """Version-2 JSON for a version-0 (lock-file timestamp) or version-1 document.

    The retired shared timestamp guarded every actor and type at once; seeding every
    cooldown with it keeps that protection until it expires instead of reading its
    absence as "never sent".
    """
    version = raw.get('version')
    legacy = raw.get('sent_at') if version is None else raw.get('legacy_sent_at')
    cooldowns = dict(raw.get('cooldowns', {})) if version == 1 else {}
    if legacy is not None:
        stamp = float(legacy)
        for key in COOLDOWN_KEYS:
            cooldowns[key] = max(float(cooldowns.get(key, stamp)), stamp)
    document = {
        'version': 2,
        'boot': boot,
        'cooldowns': cooldowns,
        'actors': raw.get('actors', {}),
        'last_delivery': raw.get('last_delivery'),
    }
    return json.dumps(document)


def select_lock(directory: Path, boot_id: str) -> Path:
    """Use `potions.lock`; keep sharing `merc-input.lock` with instances started earlier in the same boot."""
    new, old = directory / LOCK_NAME, directory / LEGACY_LOCK_NAME
    if new.exists() or not old.exists():
        return new
    for source in (directory / LEDGER_NAME, old):
        try:
            data = json.loads(source.read_text()) if source.exists() else None
        except OSError, ValueError:
            continue
        if isinstance(data, dict) and 'boot' in data:
            return old if data['boot'] == boot_id else new
    return new


class LedgerTransaction:
    """Mutable view of the ledger; `save` publishes now, the ledger publishes at exit only when dirty."""

    def __init__(self, path: Path, data: LedgerData, *, dirty: bool = False) -> None:
        self.path = path
        self.data = data
        self._migrated = dirty
        self._baseline = copy.deepcopy(data)

    @property
    def dirty(self) -> bool:
        return self._migrated or self.data != self._baseline

    def save(self) -> None:
        publish(self.path, self.data.model_dump(mode='json'))
        self._migrated = False
        self._baseline = copy.deepcopy(self.data)


class PotionLedger:
    def __init__(self, directory: Path, *, boot_id: str | None = None) -> None:
        self.boot_id = boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.path = directory / LEDGER_NAME
        self.legacy_path = directory / LEGACY_LOCK_NAME
        self.lock_path = select_lock(directory, self.boot_id)

    def _read(self) -> str:
        if self.path.exists():
            return self.path.read_text()
        return self.legacy_path.read_text() if self.legacy_path.exists() else ''

    def _load(self, contents: str) -> LedgerTransaction:
        raw = json.loads(contents) if contents else {}
        if not isinstance(raw, dict):
            raise ValueError('Potion ledger must be a JSON object')
        if raw.get('boot') != self.boot_id:
            # Monotonic timestamps from another boot are meaningless.
            return LedgerTransaction(self.path, LedgerData.empty(self.boot_id), dirty=True)
        version = raw.get('version')
        if version == 2:
            return LedgerTransaction(self.path, LedgerData.model_validate_json(contents))
        if version in (None, 1):
            return LedgerTransaction(self.path, LedgerData.model_validate_json(migrate(raw, self.boot_id)), dirty=True)
        raise ValueError('Unsupported potion ledger version')

    @contextmanager
    def transaction(self) -> Generator[LedgerTransaction]:
        """Serialize ledger access across instances; publish at exit only if the body mutated and succeeded."""
        with self.lock_path.open('a+') as file:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            transaction = self._load(self._read())
            failed = True
            try:
                yield transaction
                failed = False
            finally:
                # A raising body must not publish partial state; the lock closes with the `with`.
                if not failed and transaction.dirty:
                    transaction.save()

    def given_at(self, actor: Actor, potion: PotionType) -> float | None:
        """When a potion of `potion` was last given to `actor` (its cooldown stamp: the healer's key, on the host's
        monotonic clock), read without the lock from the ledger as last published; None when there is none, it is of
        another boot, or it cannot be read. For a reader in another process (macros/drinking.py): never a write."""
        try:
            raw = json.loads(self._read() or '{}')
        except OSError, ValueError:
            return None
        if not isinstance(raw, dict) or raw.get('boot') != self.boot_id or not isinstance(raw.get('cooldowns'), dict):
            return None
        stamp = raw['cooldowns'].get(cooldown_key(actor, potion))
        return float(stamp) if isinstance(stamp, int | float) else None

    def claim(self, actor: Actor, potion: PotionType, now: float, *, within: float) -> Claim:
        """A drinker in another process (macros/drinking.py, the macro's) takes the potion of `potion` for `actor`
        before its key: under the lock, the cooldown stamp the healer keys on (`PotionsController._step`) is set to
        `now`, so the healer stands off for its own cooldown of that kind (one drinker per blow: the macro's key and
        the healer's 50-70 ms apart at the same 65% mark took two potions for one blow twice, run-1932-findings.md
        issue 2). Refused when a stamp of the same is younger than `within` seconds (the healer's key is in flight,
        its potion not yet gone from the belt) or the healer holds the lock past CLAIM_WAIT (it is delivering now).
        A ledger that cannot be read or written refuses nothing: the drink goes ahead, as before the claim."""
        key = cooldown_key(actor, potion)
        deadline = time.monotonic() + CLAIM_WAIT
        while True:
            try:
                with self.transaction() as transaction:
                    stamp = transaction.data.cooldowns.get(key)
                    if stamp is not None and 0.0 <= now - stamp < within:
                        return Claim(False, ago=now - stamp, why=f'its {potion} potion key {now - stamp:.2f}s ago')
                    transaction.data.cooldowns[key] = now
                    return Claim(True, stamp=now, previous=stamp)
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    return Claim(False, why='it holds the ledger (a key of its own going out)')
                time.sleep(CLAIM_POLL)
            except (OSError, ValueError, TypeError, KeyError) as error:
                return Claim(True, why=f'the ledger is unavailable ({error}): not claimed')

    def unclaim(self, actor: Actor, potion: PotionType, claim: Claim) -> None:
        """A claim whose key did not go out (`claim`) given back: the stamp it set is put back as it was, unless
        another stamp has replaced it since. Best effort: a ledger busy past CLAIM_WAIT or unavailable keeps the
        claim, which costs the healer at most its cooldown of that kind."""
        if not claim.taken or claim.stamp is None:
            return
        key = cooldown_key(actor, potion)
        deadline = time.monotonic() + CLAIM_WAIT
        while True:
            try:
                with self.transaction() as transaction:
                    cooldowns = transaction.data.cooldowns
                    if cooldowns.get(key) != claim.stamp:
                        return
                    if claim.previous is None:
                        del cooldowns[key]
                    else:
                        cooldowns[key] = claim.previous
                    return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    return
                time.sleep(CLAIM_POLL)
            except OSError, ValueError, TypeError, KeyError:
                return


@dataclass(frozen=True)
class Claim:
    """What `PotionLedger.claim` came to: `taken`, the potion is the claimant's to drink (`stamp` the stamp it set,
    `previous` the one it replaced; no stamp: the ledger was unavailable and nothing was set); not taken, the other
    drinker has it (`ago`: seconds since its stamp, when one stood in the way). `why`: said in the claimant's log."""

    taken: bool
    stamp: float | None = None
    previous: float | None = None
    ago: float | None = None
    why: str = ''
