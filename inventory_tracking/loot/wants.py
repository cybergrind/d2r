"""Layer 2 of the loot design (loot/design.md §3.1, §4.4): the demand rows, read from loot/data/wants.json (built by
loot/build_wants.py, every row sourced), and how an item's facts meet them. Pure.

A row names its bases (items.txt codes resolved from the game data at build time, or itemtypes codes), the
qualities, the conditions readable on the ground (`ground`: pick it up), the conditions that make it a keeper once
read in full (`must`, and one of `any`), and the rolls that decide its worth (`matters`). Conditions are tri-state:
True, False, or None when the facts do not hold the stat (an unread ground roll, an unidentified affix). A row with
no `must` is a pickup row only (it never makes an item a keeper).
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Literal

from inventory_tracking.loot.facts import ItemFacts


__all__ = ['WANTS_FILE', 'Need', 'RollSpec', 'Want', 'load', 'matching', 'parse', 'wants']

WANTS_FILE = Path(__file__).parent / 'data' / 'wants.json'
FACETS = frozenset(('ethereal', 'sockets', 'quality', 'identified'))


@dataclass(frozen=True)
class RollSpec:
    """One roll that decides the price or the use: its stat key, the direction that is better, the range it rolls in
    and the value from which it is 'good' (paid). `facet` rolls (ethereal, sockets) are matched, not ranked."""

    key: str  # 'id:layer', or a facet: 'ethereal', 'sockets'
    label: str
    low: int
    high: int
    better: Literal['higher', 'lower', 'match'] = 'higher'
    good: int | None = None  # the paid floor
    source: str = ''
    scale: int = 1  # raw / scale is the shown value (maxhp is kept in 256ths)


@dataclass(frozen=True)
class Need:
    """One condition: the most of `keys` (stat 'id:layer' keys) or a facet, at least `min`, at most `max`, one of
    `among`, or equal to `equals`. Raw values are divided by `scale` first."""

    keys: tuple[str, ...]
    min: int | None = None
    max: int | None = None
    among: tuple[Any, ...] | None = None
    equals: Any = None
    scale: int = 1

    def value(self, facts: ItemFacts) -> Any:
        """The facts' value for this condition; None when not read."""
        if len(self.keys) == 1 and self.keys[0] in FACETS:
            return facts.facet(self.keys[0])
        found: list[int] = []
        for key in self.keys:
            stat, _, layer = key.partition(':')
            value = facts.stat(int(stat), int(layer or 0))
            if value is None:
                return None
            found.append(value)
        return max(found) // self.scale if found else None

    def holds(self, facts: ItemFacts) -> bool | None:
        value = self.value(facts)
        if value is None:
            return None
        if self.equals is not None and value != self.equals:
            return False
        if self.among is not None and value not in self.among:
            return False
        if self.min is not None and value < self.min:
            return False
        return not (self.max is not None and value > self.max)

    def said(self, facts: ItemFacts | None = None) -> str:
        name = '|'.join(self.keys)
        bound = (
            f'={self.equals}' if self.equals is not None
            else f' in {list(self.among)}' if self.among is not None
            else f'>={self.min}' if self.max is None
            else f'<={self.max}' if self.min is None
            else f' {self.min}-{self.max}'
        )  # fmt: skip
        read = f' (read {self.value(facts)})' if facts is not None else ''
        return f'{name}{bound}{read}'


def _all(needs: Sequence[Need], facts: ItemFacts) -> bool | None:
    """True when every need holds, False when one fails, else None (one unread)."""
    results = [need.holds(facts) for need in needs]
    if any(result is False for result in results):
        return False
    return None if any(result is None for result in results) else True


def _one(needs: Sequence[Need], facts: ItemFacts) -> bool | None:
    """True when a need holds (or there are none), False when all fail, else None."""
    if not needs:
        return True
    results = [need.holds(facts) for need in needs]
    if any(result is True for result in results):
        return True
    return None if any(result is None for result in results) else False


@dataclass(frozen=True)
class Want:
    """A demand row: who uses it (build slot, merc slot, runeword base, trade) and what it must have."""

    id: str
    klass: str  # the design's pickup class (G1-G13) or 'own' for an own-use row
    who: Literal['warlock', 'merc', 'runeword-base', 'trade']
    label: str
    codes: frozenset[str] = frozenset()
    types: frozenset[str] = frozenset()
    names: frozenset[str] = frozenset()  # unique/set names (own-use rows)
    qualities: frozenset[str] = frozenset()
    ground: tuple[Need, ...] = ()
    must: tuple[Need, ...] | None = None  # None: a pickup row only
    any: tuple[Need, ...] = ()
    then: Literal['keep', 'identify'] = 'keep'
    always_keep: bool = False  # BiS rows: kept whatever the copies
    must_have: bool = False  # on the ground: a valuable the loop does not leave
    matters: tuple[RollSpec, ...] = ()
    asks: Mapping[str, Any] | None = field(default=None, compare=False)
    source: str = ''

    def applies(self, facts: ItemFacts) -> bool:
        """Whether the row is about this item at all: its base, quality and name."""
        if self.codes and facts.code not in self.codes:
            return False
        if self.types and facts.base_type not in self.types:
            return False
        if self.qualities and facts.quality_name not in self.qualities:
            return False
        return not (self.names and facts.name not in self.names)

    def picks(self, facts: ItemFacts) -> bool | None:
        """On the ground: whether its ground conditions hold (None: a roll not read)."""
        return _all(self.ground, facts) if self.applies(facts) else False

    def holds(self, facts: ItemFacts) -> bool | None:
        """Read in full: whether it is a keeper by this row (None: a roll not read; False for a pickup row)."""
        if self.must is None or not self.applies(facts):
            return False
        every, one = _all(self.must, facts), _one(self.any, facts)
        if every is False or one is False:
            return False
        return None if every is None or one is None else True


def _need(row: Mapping[str, Any]) -> Need:
    keys = tuple(row['keys']) if 'keys' in row else (row['key'],)
    among = row.get('in')
    return Need(keys, row.get('min'), row.get('max'), tuple(among) if among is not None else None,
                row.get('equals'), row.get('scale', 1))  # fmt: skip


def _spec(row: Mapping[str, Any]) -> RollSpec:
    return RollSpec(row['key'], row['label'], row['low'], row['high'], row.get('better', 'higher'), row.get('good'),
                    row.get('source', ''), row.get('scale', 1))  # fmt: skip


def parse(row: Mapping[str, Any]) -> Want:
    """A wants.json row as a `Want`."""
    must = row.get('must')
    return Want(
        id=row['id'],
        klass=row['class'],
        who=row['who'],
        label=row['label'],
        codes=frozenset(row.get('codes', ())),
        types=frozenset(row.get('types', ())),
        names=frozenset(row.get('names', ())),
        qualities=frozenset(row.get('qualities', ())),
        ground=tuple(_need(n) for n in row.get('ground', ())),
        must=tuple(_need(n) for n in must) if must is not None else None,
        any=tuple(_need(n) for n in row.get('any', ())),
        then=row.get('then', 'keep'),
        always_keep=row.get('always_keep', False),
        must_have=row.get('must_have', False),
        matters=tuple(_spec(s) for s in row.get('matters', ())),
        asks=row.get('asks'),
        source=row['source'],
    )


def load(path: Path = WANTS_FILE) -> tuple[Want, ...]:
    data = json.loads(path.read_text())
    return tuple(parse(row) for row in data['rows'])


@cache
def wants() -> tuple[Want, ...]:
    """The built rows (loot/data/wants.json), read once."""
    return load()


def matching(facts: ItemFacts, rows: Sequence[Want] | None = None) -> tuple[Want, ...]:
    """The rows `facts` is a keeper by (`holds` True)."""
    return tuple(row for row in (wants() if rows is None else rows) if row.holds(facts) is True)
