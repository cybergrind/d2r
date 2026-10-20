"""Layer 3 of the loot design (loot/design.md §4): whether a drop on the ground is picked up, and what then. Pure.

`judge(facts)` answers a `GroundVerdict`: picked or left, a must-have (the loop does not leave the game with it) or
not, and `then`: KEEP (its ground facts decide) or IDENTIFY (its value needs the identified read). The classes:

- G1 sure valuables: runes, gems, charms, jewels (today's GOOD pickup)
- G2 uniques and sets: always, identified then judged (K3-K6)
- G3-G13 the wants rows with ground conditions or an identify class (loot/data/wants.json): merc eth polearms and
  armor, white Monarchs, magic Monarchs, Paladin shields, Void daggers, Warlock class items, circlets, jewelry, blues

A wanted base whose rolls were not read is left ("unread bases filled the stash", 2026-10-17). Low quality is
always left. M1: only the shadow log reads it (loot/shadow.py); the pickup is macros/pickmode.py's until M5.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.loot.facts import LOW, SET, UNIQUE, ItemFacts
from inventory_tracking.loot.keep import CHARMS, GEMS, JEWELS, RUNES, SUNDER
from inventory_tracking.loot.value import Value
from inventory_tracking.loot.wants import Want, wants


__all__ = ['GroundVerdict', 'Then', 'judge']


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


def judge(facts: ItemFacts, value: Value | None = None, rows: Sequence[Want] | None = None) -> GroundVerdict:
    """The ground verdict on `facts` (the module text); `value` (an appraisal before the pickup) is unused in M1."""
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
    unread, picked = False, []
    for row in wants() if rows is None else rows:
        if not _pickup_row(row) or not row.applies(facts):
            continue
        took = row.picks(facts)
        if took is None:
            unread = True
        elif took:
            picked.append(row)
    if not picked:
        return _left('its rolls are not read' if unread else 'no class takes it')
    best = max(picked, key=lambda row: (row.always_keep, row.must_have, bool(row.ground)))
    # A must-have only by conditions read and met: a row picking by base alone (every magic Monarch) says nothing
    must = facts.marked or any(row.must_have and row.ground for row in picked)
    return GroundVerdict(True, must, _then(facts), best.klass, best.label)
