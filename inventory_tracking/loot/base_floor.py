"""The plain base gate: whether a white or superior base is worth its cells, by the offline KB's price for the facts
read (its base, quality, sockets, ethereal flag and ED grade), not by the loot filter showing it. Pure but for the
table's one read (loot/data/base-floor.json, built by loot/build_base_floor.py from pricing/triage).

BASE_FLOOR (the player, 2026-10-23: "and also, we're wasting our inventory space with flails, what for? are we going
to end run because there is no space?"; "what are these flails? they are like 1 jah each?"; "we don't know what is
cost and going to ruin all our inventory space? for base that doesn't cost anything?"; and "we absolutely must
preserve top items", "make sure that you understand, that we absolutely MUST NOT trash good items"): a plain base whose
fitting bucket the table names (priced clearly under FLOOR_IST, the first-copy worth-the-cells floor of keep.py
FIRST_COPY_USABLE_ONLY, appraised SELLS_OVER, no demand row) is left on the ground (macros/pickmode.py `kept`) and
sold in town (keep.py K9). Asymmetric: any doubt keeps it - an unread socket count, ethereal flag or superior ED, a
staff mod, skill tab or resistance automod the bucket does not price (unless the wants rows judged them, the ground
read's `base_verdict`), a key the table lacks (no band, thin, a relaxed facet, a demand row). False: the filter's
"shown" alone takes a base, as before.
"""

import json
import os
import sys
from collections.abc import Mapping, Sequence
from contextlib import suppress
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Drop
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.loot.facts import (
    DAMAGE_PERCENT,
    DEFENSE_PERCENT,
    NORMAL,
    RESISTS,
    SINGLE_SKILL,
    SKILL_TAB,
    SUPERIOR,
    ItemFacts,
)
from inventory_tracking.loot.value import DUPLICATE_IST


__all__ = [
    'BASE_FLOOR',
    'FLOOR_IST',
    'GAME',
    'PICKUPS',
    'PICKUP_IST',
    'PLAIN_BY_RULES',
    'SELLS_OVER',
    'TABLE',
    'allowed',
    'allowed_by',
    'allowed_rows',
    'denied',
    'denied_rows',
    'drop_junk',
    'facts_junk',
    'is_plain',
    'junk',
    'kb_keeps',
    'kb_match',
    'key',
    'lower_keys',
    'pickups',
    'remember',
    'remembered',
    'seen',
    'table',
    'town_junk',
    'town_kept',
    'unread',
]

BASE_FLOOR = True
# The plain bases by the allowlist (loot/data/base-pickups.json, loot/build_base_pickups.py, rca/2026-10-23/
# base-pickups.md; the player, 2026-10-23 ~00:50: "redo the home work, you must sytseematically collect each white/grey
# base that we're going to pickup, every base must worth 4+ist at least / we need to pickup something like +45 all
# res, 4os sacret target and so on. or 3os grey kris with +3 abyss (and, probably, even other synergy)"; "0os crystal
# sword is a trash!", "+1 skill knife - is a trash"; earlier, ~00:40, "random daggers, 2os/1os", "a lot of random book,
# random armors", "targe with +9 all res", "random white circlet"): in every pickup level a shown white or grey weapon
# or armor is taken only when an allowlist entry matches the facts its ground read gives (`allowed`); anything else is
# left, unread facts included ("unread bases filled the stash", 2026-10-17). Wirt's Leg aside; what the loot marks
# point at goes the usual path. Moved here from macros/pickmode.py (2026-10-23, phase 2A: one home; loot/assess.py
# GROUND reads it). False: the MOST level takes whatever the filter shows (`drop_junk` alone leaves the KB's junk)
PLAIN_BY_RULES = True
FLOOR_IST = DUPLICATE_IST  # 1 Ist: under it a first copy no build names is given up (keep.py FIRST_COPY_USABLE_ONLY)
SELLS_OVER = frozenset(('vendor', 'slow'))  # keep.py FIRST_COPY_SELLS_OVER: `check`, `sell`, `self`, `keep` are kept
TABLE = Path(__file__).parent / 'data' / 'base-floor.json'
# The allowlist (loot/build_base_pickups.py; the player, 2026-10-23 ~00:50: "every base must worth 4+ist at least"):
# the only white and grey weapons and armor PLAIN_BY_RULES picks, and keep.py K9 keeps
PICKUPS = Path(__file__).parent / 'data' / 'base-pickups.json'
PICKUP_IST = 4.0
CATEGORIES = frozenset(('weapons', 'armor'))
NEVER_CODES = frozenset(('leg',))  # Wirt's Leg (keep.py NEVER_SOLD_CODES), a club by its type
PERFECT_ED = 15  # a superior's best ED roll: the premium buckets (">= 15 ED")
# Rolls a plain bucket does not price: class skills and staff mods, skill tabs, resistance automods (itemstatcost ids:
# 83 item_addclassskills, 97 item_nonclassskill, 126 item_elemskill, besides loot/facts.py's)
UNPRICED = frozenset((SINGLE_SKILL, SKILL_TAB, 83, 97, 126, *RESISTS))
QUALITY = {NORMAL: 'normal', SUPERIOR: 'superior'}


def key(code: str, rarity: str, *, ethereal: bool, sockets: int, perfect: bool) -> str:
    """The table's key: 'fla/superior/noneth/0os/ordinary'."""
    return f'{code}/{rarity}/{"eth" if ethereal else "noneth"}/{sockets}os/{"perfect" if perfect else "ordinary"}'


@cache
def table() -> Mapping[str, Any]:
    """The built table; empty (every base kept) when unreadable."""
    try:
        return json.loads(TABLE.read_text())
    except (OSError, ValueError) as error:
        LOG.info('Macro: base floor: no table (%s): every plain base kept', error)
        return {}


@cache
def _categories() -> Mapping[str, str]:
    return {base['code']: base.get('category', '') for base in metadata()['bases'].values()}


def junk(code: str, quality: int, *, ethereal: bool | None, sockets: int | None, ed: int | None) -> str | None:
    """Why a plain base of these facts is not worth its cells, None when it is kept (any fact unread, BASE_FLOOR off,
    a key the table lacks). Pure but for the table."""
    rarity = QUALITY.get(quality)
    if not BASE_FLOOR or rarity is None or code in NEVER_CODES or _categories().get(code) not in CATEGORIES:
        return None
    if ethereal is None or sockets is None or (rarity == 'superior' and ed is None):
        return None
    perfect = rarity == 'superior' and (ed or 0) >= PERFECT_ED
    found = (table().get('junk') or {}).get(key(code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect))
    if not found:
        return None
    return (
        f'a plain base under the floor: asks {found["q1"]:g}-{found["median"]:g} Ist ({found["sellers"]} sellers, '
        f'{found["observed"]}), {found["verdict"]}, under {FLOOR_IST:g} Ist'
    )


def kb_keeps(drop: Drop, *, price_only: bool = False) -> str | None:
    """Why the KB keeps a shown white or superior weapon or armor by its ground read whatever the rules say (a keep key
    of the table: a band at or above FLOOR_IST, thin or pooled, or a runeword or merc base a guide recommends for
    exactly its facts), None when it does not (no such key: PLAIN_BY_RULES leaves it).
    `price_only`: a rule judged the base and left it (the Void daggers' staff mods, a shield's resistances): only a
    price at or above the floor overrules it, not a guide's runeword. Unread facts are the caller's (doubt keeps)."""
    found, base = drop.rolls, item_base(drop.txt) if drop.txt else None
    rarity = QUALITY.get(drop.quality)
    if found is None or base is None or rarity is None:
        return None
    ed = 0 if drop.quality == NORMAL else found.damage if base.get('category') == 'weapons' else found.defense
    perfect = rarity == 'superior' and (ed or 0) >= PERFECT_ED
    record = (table().get('keep') or {}).get(
        key(base['code'], rarity, ethereal=found.ethereal, sockets=found.sockets, perfect=perfect)
    )
    if not record:
        return None
    priced = max(record.get('median') or 0, record.get('q1') or 0) >= FLOOR_IST
    # A guide's runeword or merc base the triage itself calls `vendor` (a plain 4os Grand Matron Bow, Faith): no keeper
    if not priced and (price_only or not record.get('demand') or record.get('verdict') == 'vendor'):
        return None
    if record.get('demand') and not (price_only or priced):
        return f'a base the guides want ({", ".join(record["demand"])})'
    return f'a base the KB keeps: asks {record["q1"]:g}-{record["median"]:g} Ist ({record["observed"]})'


def unread(drop: Drop) -> str | None:
    """Which fact of the plain base decision the ground read lacks, None when all are read (macros/pickmode.py: doubt
    keeps it)."""
    found, base = drop.rolls, item_base(drop.txt) if drop.txt else None
    if found is None:
        return 'its rolls'
    weapon = base is not None and base.get('category') == 'weapons'
    if drop.quality == SUPERIOR and base is not None and (found.damage if weapon else found.defense) is None:
        return 'its ED'
    return None


def drop_junk(drop: Drop, *, judged: bool = False) -> str | None:
    """`junk` for a white or superior drop the loot filter shows, by its ground read (`Drop.rolls`). `judged`: the wants
    rows read and left its staff mods, tabs or resistances (loot/ground_judge.py `base_verdict`), so the base alone is
    priced; else any such roll keeps it."""
    found = drop.rolls
    if drop.source != 'shown' or drop.prized or found is None or drop.quality not in QUALITY:
        return None
    base = item_base(drop.txt) if drop.txt else None
    if base is None:
        return None
    if not judged and (found.skills or found.tabs or found.resists):
        return None
    ed = 0 if drop.quality == NORMAL else found.damage if base.get('category') == 'weapons' else found.defense
    return junk(base['code'], drop.quality, ethereal=found.ethereal, sockets=found.sockets, ed=ed)


def _stat(name: str) -> int | None:
    head = name.split(':')[0]
    return int(head) if head.isdigit() else None


def facts_junk(facts: ItemFacts) -> str | None:
    """`junk` for an item's facts (keep.py K9): white or superior, identified, its sockets, ethereal flag and (for a
    superior) ED read, and no roll a plain bucket does not price."""
    if facts.quality not in QUALITY or not facts.identified or facts.rolls is None or facts.runeword:
        return None  # a runeword is no plain base (D12, 2026-10-23)
    if _unpriced(facts):
        return None
    category = _categories().get(facts.code)
    ed = facts.stat(DAMAGE_PERCENT if category == 'weapons' else DEFENSE_PERCENT)
    return junk(facts.code, facts.quality, ethereal=facts.ethereal, sockets=facts.sockets,
                ed=0 if facts.quality == NORMAL else ed)  # fmt: skip


@cache
def pickups() -> Mapping[str, Any]:
    """The built allowlist; empty (no plain base allowed) when unreadable."""
    try:
        return json.loads(PICKUPS.read_text())
    except (OSError, ValueError) as error:
        LOG.info('Macro: base pickups: no allowlist (%s): no plain base allowed', error)
        return {}


@cache
def _allowed_rows() -> tuple[Any, ...]:
    from inventory_tracking.loot.wants import wants

    return allowed_rows(pickups(), wants())


@cache
def _denied_rows() -> tuple[tuple[Any, Mapping[str, Any]], ...]:
    return denied_rows(pickups())


def allowed_rows(doc: Mapping[str, Any], wanted: Sequence[Any]) -> tuple[Any, ...]:
    """The rows an allowlist `doc` takes by: the wants rows `wanted` it names, then its own rules. Pure."""
    from inventory_tracking.loot.wants import parse

    names = doc.get('rows') or {}
    return (*(row for row in wanted if row.id in names), *(parse(row) for row in (doc.get('custom') or {}).values()))


def denied_rows(doc: Mapping[str, Any]) -> tuple[tuple[Any, Mapping[str, Any]], ...]:
    """The failing facets an allowlist `doc` leaves whatever its entries say, as (row, entry). Pure."""
    from inventory_tracking.loot.wants import parse

    return tuple((parse(entry), entry) for entry in (doc.get('denied') or {}).values())


def is_plain(code: str, quality: int) -> bool:
    """Whether a `quality` item of base `code` is a plain base: a white or grey weapon or armor, Wirt's Leg aside."""
    return quality in QUALITY and code not in NEVER_CODES and _categories().get(code) in CATEGORIES


def _unpriced(facts: ItemFacts) -> bool:
    return any(value and _stat(name) in UNPRICED for name, value in (facts.rolls or {}).items())


def denied(facts: ItemFacts, rows: Sequence[tuple[Any, Mapping[str, Any]]] | None = None) -> str | None:
    """Why a failing facet leaves the plain base `facts` whatever an entry says (the player, 2026-10-23: "Sales-backed
    now", per facet: an eth 4os normal Archon Plate sells 2.58 Ist), None when none does. A plain facet's denial holds
    only for a base with no roll a plain bucket does not price (a staff mod, a skill tab, a resistance)."""
    for row, entry in _denied_rows() if rows is None else rows:
        if entry.get('plain') and _unpriced(facts):
            continue
        if row.applies(facts) and row.picks(facts) is True:
            return f'denied: {row.label} ({_evidence(entry["evidence"])})'
    return None


def allowed(facts: ItemFacts) -> str | None:
    """Why the allowlist takes the plain base `facts` (an entry matching its facts read), None when none does or a
    failing facet denies it (`allowed_by` over loot/data/base-pickups.json)."""
    return allowed_by(facts, pickups(), _allowed_rows(), _denied_rows())


def allowed_by(
    facts: ItemFacts, doc: Mapping[str, Any], rows: Sequence[Any], refused: Sequence[tuple[Any, Mapping[str, Any]]]
) -> str | None:
    """`allowed` by an allowlist `doc`, its `rows` (`allowed_rows`) and its denied facets `refused` (`denied_rows`):
    no denied facet matches, then a row whose ground conditions all hold (a roll unread is no match), or a KB key of
    its exact facts. Pure but for the game data (loot/build_base_pickups.py builds on it)."""
    if denied(facts, refused) is not None:
        return None
    for row in rows:
        if row.applies(facts) and row.picks(facts) is True:
            evidence = ((doc.get('rows') or {}).get(row.id) or (doc.get('custom') or {})[row.id])['evidence']
            return f'allowlisted: {row.label} ({_evidence(evidence)})'
    rarity = QUALITY.get(facts.quality)
    category = _categories().get(facts.code)
    ed = 0 if facts.quality == NORMAL else facts.stat(DAMAGE_PERCENT if category == 'weapons' else DEFENSE_PERCENT)
    if rarity is None or facts.ethereal is None or facts.sockets is None or ed is None:
        return None
    perfect = rarity == 'superior' and ed >= PERFECT_ED
    found = kb_match(facts.code, rarity, ethereal=facts.ethereal, sockets=facts.sockets, perfect=perfect, doc=doc)
    return f'allowlisted: {found["facts"]} ({_evidence(found)})' if found else None


def lower_keys(code: str, rarity: str, *, ethereal: bool, sockets: int, perfect: bool) -> list[str]:
    """The KB keys a copy of these facts is worth at least, best first: its own; a 15 ED superior's ordinary twin; a
    superior's normal twin (the same ethereal flag and sockets). Pure."""
    keys = [key(code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect)]
    if rarity == 'superior' and perfect:
        keys.append(key(code, rarity, ethereal=ethereal, sockets=sockets, perfect=False))
    if rarity == 'superior':
        keys.append(key(code, 'normal', ethereal=ethereal, sockets=sockets, perfect=False))
    return keys


def kb_match(
    code: str, rarity: str, *, ethereal: bool, sockets: int, perfect: bool, doc: Mapping[str, Any] | None = None
) -> Mapping[str, Any] | None:
    """The allowlist KB entry these facts match: their own key, else the first lower one (`lower_keys`: a better copy
    is worth at least the worse one; the verifier, rca/2026-10-23/base-pickups-verify.md "MISSED": a 15 ED eth 6os War
    Pike was left though its ordinary twin is 119.9 Ist). A key proved under PICKUP_IST by its own split evidence or its
    facet's (base-pickups.json 'kb_dropped', a denied facet's 'keys') stops the walk: no lower key overrules it. None:
    no entry. `doc`: the allowlist (None: the built one)."""
    found_doc = pickups() if doc is None else doc
    kb, dropped = found_doc.get('kb') or {}, found_doc.get('kb_dropped') or {}
    refused = {name for entry in (found_doc.get('denied') or {}).values() for name in entry.get('keys') or ()}
    for found in lower_keys(code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect):
        if found in kb:
            return kb[found]
        if found in dropped or found in refused:
            return None
    return None


def _evidence(evidence: Mapping[str, Any]) -> str:
    kind = evidence.get('kind') or 'asks'
    return (
        f'{kind} {evidence.get("q1_ist")}-{evidence["median_ist"]} Ist, n={evidence["n"]}, {evidence.get("observed")}'
    )


# The allowlisted bases the pickup took, by game and unit ('<game>/<unit>': unit ids repeat across games): the town
# keeps them though its own read lacks their facts (keep.py K8, K9); kept across serve's restarts in TAKEN_FILE beside
# the loop's other state, at most TAKEN_MOST. GAME: the game the pickup looked at last (`seen`), the town's game
LIVE_TAKEN_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'base-pickups-taken.json'
TAKEN_FILE = LIVE_TAKEN_FILE  # injectable: tests set their own (tests/inventory_tracking/conftest.py)
TAKEN_MOST = 500
TAKEN: dict[str, str] = {}
GAME: list[str | None] = [None]


def game_name(game: object) -> str | None:
    """The game's name of a Loot's `game` (name, or (name, number)), None out of a game."""
    if isinstance(game, tuple):
        game = game[0] if game else None
    return None if game is None else str(game)


def seen(game: object) -> None:
    """Note the game the pickup looks at (macros/pickmode.py `_taken`): the town's `remembered` asks within it."""
    GAME[0] = game_name(game)


def _taken_key(game: str | None, unit_id: int) -> str:
    return f'{game}/{unit_id}'


def _taken_read() -> dict[str, str]:
    if not TAKEN:
        with suppress(OSError, ValueError, AttributeError):
            TAKEN.update({str(unit): str(why) for unit, why in json.loads(TAKEN_FILE.read_text()).items()})
    return TAKEN


def remember(unit_id: int, why: str, game: object = None) -> None:
    """Note an allowlisted base taken (`allowed`) in `game` (None: the game `seen` last); a test run writes no file."""
    taken = _taken_read()
    named = game_name(game) if game is not None else GAME[0]
    found = _taken_key(named, unit_id)
    if taken.get(found) == why:
        return
    taken[found] = why
    while len(taken) > TAKEN_MOST:
        taken.pop(next(iter(taken)))
    if TAKEN_FILE == LIVE_TAKEN_FILE and ('PYTEST_CURRENT_TEST' in os.environ or 'pytest' in sys.modules):
        return  # a test or a script on the tests' helpers never writes the live record (tests: their own tmp file)
    try:
        TAKEN_FILE.write_text(json.dumps(taken))
    except OSError as error:
        LOG.info('Macro: base pickups: the taken bases not written (%s)', error)


def remembered(unit_id: int, game: object = None) -> str | None:
    """Why the pickup took the allowlisted base `unit_id` in `game` (None: the game `seen` last), None when it did not
    (or not known, or in another game)."""
    named = game_name(game) if game is not None else GAME[0]
    return _taken_read().get(_taken_key(named, unit_id))


def town_kept(facts: ItemFacts) -> str | None:
    """keep.py K8's guard: why the loop's plain base `facts` is kept whatever its appraisal says (the pickup took it
    by the allowlist in this game, or the town's full read matches an entry), None else."""
    if not BASE_FLOOR or not is_plain(facts.code, facts.quality):
        return None
    if (why := remembered(facts.unit_id)) is not None:
        return f'taken by the allowlist in the field: {why}'
    try:
        return allowed(facts)
    except Exception as error:  # the allowlist unreadable: the other rules decide
        LOG.info('Macro: base pickups: no allowlist for the town (%s)', error)
        return None


def town_junk(facts: ItemFacts) -> str | None:
    """keep.py K9: why the loop's plain base `facts` is sold in town (on no allowlist entry by its facts, not taken by
    the allowlist), None when it is kept or is no plain base. Never runes, gems, charms, jewels, uniques, sets (not
    plain bases) or the player's (keep.py K0 first)."""
    if not BASE_FLOOR or not is_plain(facts.code, facts.quality) or remembered(facts.unit_id) is not None:
        return None
    if facts.runeword:
        return None  # a runeword is no plain base (D12, 2026-10-23)
    if allowed(facts) is not None:
        return None
    return 'a plain base on no allowlist entry (loot/data/base-pickups.json, 4+ Ist): sold'
