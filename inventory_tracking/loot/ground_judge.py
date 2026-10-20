"""Layer 3 of the loot design (loot/design.md §4): whether a drop on the ground is picked up, and what then. Pure.

`judge(facts)` answers a `GroundVerdict`: picked or left, a must-have (the loop does not leave the game with it) or
not, and `then`: KEEP (its ground facts decide) or IDENTIFY (its value needs the identified read). The classes:

- G1 sure valuables: runes, gems, charms, jewels (today's GOOD pickup)
- G2 uniques and sets: always, identified then judged (K3-K6)
- G3-G13 the wants rows with ground conditions or an identify class (loot/data/wants.json): merc eth polearms and
  armor, white Monarchs, magic Monarchs, Paladin shields, Void daggers, Warlock class items, circlets, jewelry, blues

A wanted base whose rolls were not read is left ("unread bases filled the stash", 2026-10-17). Low quality is
always left. M1: only the shadow log reads it (loot/shadow.py). M5 (`BASES`, `base_verdict`): the live pickup
(macros/pickmode.py `ground_base`) takes the white and superior bases of BASE_CLASSES this judge picks, and no other.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.loot.facts import LOW, NORMAL, SET, SUPERIOR, UNIQUE, ItemFacts
from inventory_tracking.loot.keep import CHARMS, GEMS, JEWELS, RUNES, SUNDER
from inventory_tracking.loot.value import Value
from inventory_tracking.loot.wants import Want, wants


__all__ = ['BASES', 'BASE_CLASSES', 'LEFT_ROWS', 'GroundVerdict', 'OwnedCount', 'Then', 'base_verdict', 'judge']

# M5 on (loot/design.md §7; the player, 2026-10-20 ~11:55: "bases or blue/rare items might take much place (like
# spears, matron bow) -- we want to check them and drop in the middle of the run", ~12:00 "start all three"; earlier
# "no bad bases", "best 4os eth merc bases"). True: the live pickup takes a white or superior base only by its ground
# read and the wants rows below (macros/pickmode.py `ground_base`), the cell cap lifted for them (a polearm is 2x4);
# every other white base is left. False: today's dagger and shield rules alone (pickmode.py `void_base`, `shield_base`)
BASES = True
# The base classes of design.md §4.2 the ground read decides: G3 merc eth polearms, G4 merc / runeword armor, G5 white
# Monarchs, G7 Paladin shields (the Exile base too), G8 Void daggers, G16 the market-only bases (Q7: Superior 15 ED with
# the exact sockets), G17 the merc's Cure helm (the player's own-use bases, ~12:15)
BASE_CLASSES = frozenset(('G3', 'G4', 'G5', 'G7', 'G8', 'G16', 'G17'))
# Rows no pickup takes all the same (`judge`'s default rows). Empty since 2026-10-20 ~12:50 (the player: "I want to
# keep more monarch bases"): the Spirit base row (spirit-monarch-plain-4os) left Q8's "keep one" for a cap, its
# `keep_up_to` (build_wants.py SPIRIT_MONARCH_CAP), counted by `owned` below
LEFT_ROWS: frozenset[str] = frozenset()
# The owned copies of a base for a row's `keep_up_to` (live: loot/value.py `owned_bases`, a read-only collection
# count); None: not counted, and the cap does not hold (S8)
OwnedCount = Callable[[ItemFacts], int | None]
WHITE_QUALITIES = frozenset((NORMAL, SUPERIOR))


class Then(StrEnum):
    KEEP = 'keep'  # the ground facts decide: stash it
    IDENTIFY = 'identify'  # identified (field scroll or Cain), then `keep.decide`


@dataclass(frozen=True)
class GroundVerdict:
    pick: bool
    must_have: bool
    then: Then | None  # None when left
    klass: str  # 'G8', or '' when left
    reason: str

    def said(self) -> str:
        if not self.pick:
            return f'leave ({self.reason})'
        return f'pick {self.klass} {self.then.value if self.then else ""}{" must-have" if self.must_have else ""}'


def _left(reason: str) -> GroundVerdict:
    return GroundVerdict(False, False, None, '', reason)


def _then(facts: ItemFacts) -> Then:
    return Then.KEEP if facts.identified else Then.IDENTIFY


def _pickup_row(row: Want) -> bool:
    return bool(row.ground) or row.then == 'identify'


def _capped(row: Want, facts: ItemFacts, owned: OwnedCount | None) -> int | None:
    """The owned count when `row` keeps copies only up to `keep_up_to` and that many are owned, else None."""
    if row.keep_up_to is None or owned is None:
        return None
    count = owned(facts)
    return count if count is not None and count >= row.keep_up_to else None


def judge(
    facts: ItemFacts,
    value: Value | None = None,
    rows: Sequence[Want] | None = None,
    owned: OwnedCount | None = None,
) -> GroundVerdict:
    """The ground verdict on `facts` (the module text); `value` (an appraisal before the pickup) is unused in M1;
    `owned` counts the owned copies for a row with `keep_up_to` (None: no count, the cap does not hold)."""
    del value
    if facts.quality == LOW:
        return _left('low quality')
    kind = facts.base_type
    if kind in RUNES | GEMS | SUNDER:
        return GroundVerdict(True, facts.marked, Then.KEEP, 'G1', 'a rune or gem')
    if kind in CHARMS | JEWELS:
        named = facts.quality in (SET, UNIQUE)
        return GroundVerdict(True, facts.marked or named, _then(facts), 'G1', 'a charm or jewel')
    if facts.quality in (SET, UNIQUE):
        return GroundVerdict(True, True, _then(facts), 'G2', 'a unique or set item')
    unread, picked, full = False, [], None
    for row in [row for row in wants() if row.id not in LEFT_ROWS] if rows is None else rows:
        if not _pickup_row(row) or not row.applies(facts):
            continue
        took = row.picks(facts)
        if took is None:
            unread = True
        elif took and (count := _capped(row, facts, owned)) is not None:
            full = f'{count} owned, {row.keep_up_to} kept at most: {row.label}'
        elif took:
            picked.append(row)
    if not picked:
        return _left('its rolls are not read' if unread else full or 'no class takes it')
    best = max(picked, key=lambda row: (row.always_keep, row.must_have, bool(row.ground)))
    # A must-have only by conditions read and met: a row picking by base alone (every magic Monarch) says nothing
    must = facts.marked or any(row.must_have and row.ground for row in picked)
    return GroundVerdict(True, must, _then(facts), best.klass, best.label)


def base_verdict(
    facts: ItemFacts, rows: Sequence[Want] | None = None, owned: OwnedCount | None = None
) -> GroundVerdict | None:
    """M5: the verdict on a white or superior base the ground read decides (a pick by a row of BASE_CLASSES, LEFT_ROWS
    aside), None for any other item or with BASES off. A base no row picks, whose rolls were not read, or whose row's
    cap the `owned` copies reach, is a leave verdict: the live pickup leaves it."""
    if not BASES or facts.quality not in WHITE_QUALITIES:
        return None
    found = [
        row for row in (wants() if rows is None else rows) if row.klass in BASE_CLASSES and row.id not in LEFT_ROWS
    ]
    if not any(row.applies(facts) for row in found):
        return None
    return judge(facts, rows=found, owned=owned)
