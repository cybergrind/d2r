"""Cross-instance serialization and durable potion state (one ledger per host)."""

import copy
import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from inventory_tracking.models import Actor, PotionType, SessionIdentity
from inventory_tracking.reports import publish


Timestamp = Annotated[float, Field(ge=0, allow_inf_nan=False)]
CoreIdentity = tuple[int, str, int]
LEDGER_NAME = 'potions.json'
LOCK_NAME = 'potions.lock'
# Before version 2 the lock file was also the store for one shared timestamp.
LEGACY_LOCK_NAME = 'merc-input.lock'


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
    def transaction(self) -> Iterator[LedgerTransaction]:
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
