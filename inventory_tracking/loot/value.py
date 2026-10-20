"""Layer 2 of the loot design (loot/design.md §3): what the market and the build say an item is worth, and which of
its rolls decide that. Pure, except `CollectionCopies` (a read-only collection read).

- `value_ist`: the price by the item's own rolls (moved here from identify/service.py, which imports it back).
- `assess` / `appraise_result`: a `Value` from a price and a verdict (tests, tables) or from the identify worker's KB
  result (live).
- `matters_for`: the rolls that decide an item, wants first, else its variable rolls (§3.1).
- `better_than`: an item against its owned copies on those rolls only (§3.2).
- `CollectionCopies`: the owned copies from the collection database (macros/copies.py `owned_copies`).

Prices are the repo's (pricing/, the KB), never the web (S7).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from inventory_tracking.appraisal.owned import perfection, variable_rolls
from inventory_tracking.loot.facts import NORMAL, SUPERIOR, ItemFacts, Owner, Where, from_observation
from inventory_tracking.loot.wants import RollSpec, Want, matching


__all__ = [
    'DUPLICATE_IST',
    'KEEP_IST',
    'Appraiser',
    'Band',
    'CollectionCopies',
    'Comparison',
    'OwnedCopies',
    'RollSpec',
    'Value',
    'Want',
    'appraise_result',
    'assess',
    'better_than',
    'comparable',
    'matters_for',
    'position',
    'score',
    'tier_of',
    'value_ist',
    'worth_of',
]

# Q1 (the player's ruling of 2026-10-20 09:33, "start M0+M1", with the design's recommended answers): an item worth
# 1 Ist or more by its own rolls is expensive and its duplicates are kept ("we keep dublicates only for expensive
# items"); the 2026-10-19 "1+ ist" ruling, identify/service.py KEEP_IST, loot/build_filter.py SLOW_MINIMUM
DUPLICATE_IST = 1.0
KEEP_IST = 0.25  # pricing/data/triage/rules.json keep_ist: under it an item is worthless unless a want names it
Tier = Literal['expensive', 'cheap', 'worthless', 'unknown']


@dataclass(frozen=True)
class Band:
    """The asks' band the price comes from: lower quartile and median in Ist, sellers, the date observed."""

    q1: float | None
    median: float | None
    sellers: int | None = None
    observed: str | None = None
    kind: str = 'asks'


@dataclass(frozen=True)
class Value:
    worth_ist: float | None  # the price by its own rolls, None unknown
    band: Band | None
    verdict: str | None  # the appraisal's verdict (sell/slow/check/self/vendor), for the tier and the log
    wants: tuple[Want, ...]  # the demand rows it is a keeper by
    matters: tuple[RollSpec, ...]  # the rolls that decide it; () none known
    tier: Tier
    reason: str = ''

    def said(self) -> str:
        worth = f'{self.worth_ist:.3g} Ist' if self.worth_ist is not None else 'no price'
        return f'{worth}, {self.tier}' + (f', verdict {self.verdict}' if self.verdict else '')


class Appraiser(Protocol):
    def appraise(self, facts: ItemFacts) -> Value: ...


class OwnedCopies(Protocol):
    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None: ...  # None: cannot be told (S8)


def value_ist(result, observation=None) -> float | None:
    """The item's price in Ist by its own rolls (the player, 2026-10-19: "it should be priced according our rols"): the
    triage's own price where it compares the rolls (`roll_comparison`, `roll_placement`); else its place in the asks'
    band by its rolls, the lower quartile for the worst and the median for perfect ones (`perfection`), the median for
    fixed stats; else the estimate. None unknown."""
    triage = result.get('triage') or {}
    if (triage.get('roll_comparison') or (triage.get('roll_placement') or {}).get('valid')) and triage.get(
        'decision_ist'
    ) is not None:
        return triage['decision_ist']
    band = triage.get('band') or {}
    low, middle = band.get('q1_ist'), band.get('median_ist')
    if low is not None and middle is not None:
        place = perfection(variable_rolls(observation if observation is not None else result.get('extraction', {})))
        return middle if place is None else low + place * (middle - low)
    price = low if low is not None else middle
    return price if price is not None else (result.get('price_estimate') or {}).get('estimate_ist')


def worth_of(result: Mapping[str, Any], observation: Mapping[str, Any] | None = None) -> float | None:
    """`value_ist`, else the triage's decision price."""
    worth = value_ist(result, observation)
    return worth if worth is not None else (result.get('triage') or {}).get('decision_ist')


def tier_of(worth: float | None, verdict: str | None) -> Tier:
    """expensive at DUPLICATE_IST or more; worthless under KEEP_IST or appraised `vendor`; cheap between; unknown with
    no price and no vendor verdict (§3.3)."""
    if worth is not None and worth >= DUPLICATE_IST:
        return 'expensive'
    if verdict == 'vendor' or (worth is not None and worth < KEEP_IST):
        return 'worthless'
    return 'cheap' if worth is not None else 'unknown'


def _observed_specs(facts: ItemFacts) -> tuple[RollSpec, ...]:
    if facts.observation is None:
        return ()
    specs = []
    for key, roll in variable_rolls(dict(facts.observation)).items():
        row = roll['row']
        bounds = row.get('roll_quality_range') or row.get('roll_range')
        stats = [row['memory_stat']] if row.get('memory_stat') else row.get('memory_stats') or []
        raw, value = (stats[0].get('raw') if stats else None), row.get('value')
        scale = raw // value if isinstance(raw, int) and isinstance(value, int) and value and raw % value == 0 else 1
        if '+' in key or ':' not in key:
            continue  # a combined or unkeyed stat: not compared by key
        specs.append(RollSpec(key, row.get('name') or key, int(bounds['min']), int(bounds['max']), roll['better'],
                              source='the read (appraisal-definitions roll range)', scale=max(scale, 1)))  # fmt: skip
    return tuple(specs)


def matters_for(facts: ItemFacts, wants: Sequence[Want]) -> tuple[RollSpec, ...]:
    """The rolls that decide the item: its wants' first (loot/data/wants.json), else every variable roll of its read
    (design §3.1 source 6). The triage roll models (sources 2-5) are M2."""
    found = tuple(spec for want in wants for spec in want.matters)
    return found or _observed_specs(facts)


def assess(
    facts: ItemFacts,
    *,
    worth: float | None,
    verdict: str | None = None,
    band: Band | None = None,
    wants: Sequence[Want] | None = None,
    reason: str = '',
) -> Value:
    """A `Value` from a price and a verdict: the pure core of the appraisers."""
    matched = matching(facts) if wants is None else tuple(wants)
    return Value(worth, band, verdict, matched, matters_for(facts, matched), tier_of(worth, verdict), reason)


def appraise_result(facts: ItemFacts, result: Mapping[str, Any], verdict: str | None = None) -> Value:
    """A `Value` from the identify worker's KB result (`IdentifyWorker` `_lookup`) and its verdict."""
    triage = result.get('triage') or {}
    found = triage.get('band') or {}
    band = (
        Band(found.get('q1_ist'), found.get('median_ist'), found.get('sellers'), found.get('observed_at'),
             found.get('evidence_kind') or 'asks')
        if found else None
    )  # fmt: skip
    observation = dict(facts.observation) if facts.observation is not None else None
    return assess(facts, worth=worth_of(result, observation), verdict=verdict or triage.get('verdict'), band=band,
                  reason=triage.get('reason') or '')  # fmt: skip


def comparable(new: ItemFacts, copy: ItemFacts) -> bool:
    """Whether `copy` is the same item for a comparison: the same base, name and ethereal facet, and for a white base
    the same sockets (§3.2 step 1)."""
    if (new.code, new.name) != (copy.code, copy.name):
        return False
    if new.ethereal is not None and copy.ethereal is not None and new.ethereal != copy.ethereal:
        return False
    return not (new.quality in (NORMAL, SUPERIOR) and new.sockets != copy.sockets)


def _read(facts: ItemFacts, spec: RollSpec) -> int | None:
    stat, _, layer = spec.key.partition(':')
    if not stat.isdigit():
        return None
    value = facts.stat(int(stat), int(layer or 0))
    return None if value is None else value // spec.scale


def position(facts: ItemFacts, spec: RollSpec) -> float | None:
    """Where the roll lies in its range, 0 the worst and 1 the best."""
    value = _read(facts, spec)
    if value is None or spec.better == 'match' or spec.high <= spec.low:
        return None
    fraction = (value - spec.low) / (spec.high - spec.low)
    return max(0.0, min(1.0, fraction if spec.better == 'higher' else 1 - fraction))


def score(facts: ItemFacts, matters: Sequence[RollSpec]) -> float:
    """The summed roll positions over `matters`, the paid (`good`) rolls counted twice (§3.2 step 4)."""
    return sum((2 if spec.good is not None else 1) * (position(facts, spec) or 0.0) for spec in matters)


@dataclass(frozen=True)
class Comparison:
    """`new` against its owned copies: better only when better than every comparable copy; the per-roll lines say
    the values ('ED 50 vs 53, 56')."""

    better: bool
    copies: int  # the comparable copies
    lines: tuple[str, ...] = ()
    relations: tuple[str, ...] = field(default=())

    def said(self) -> str:
        return '; '.join(self.lines) if self.lines else 'no roll to compare'


def _relation(new: ItemFacts, copy: ItemFacts, matters: Sequence[RollSpec]) -> str:
    better = worse = 0
    for spec in matters:
        mine, theirs = _read(new, spec), _read(copy, spec)
        if mine is None or theirs is None or mine == theirs or spec.better == 'match':
            continue
        if (mine > theirs) == (spec.better == 'higher'):
            better += 1
        else:
            worse += 1
    if better and worse:
        # Q2: mixed is decided by worth (the place in the band follows the roll positions); a tie is not better
        return 'mixed-better' if score(new, matters) > score(copy, matters) else 'mixed-not-better'
    return 'better' if better else 'worse' if worse else 'equal'


def better_than(new: ItemFacts, copies: Sequence[ItemFacts], matters: Sequence[RollSpec]) -> Comparison:
    """`new` against the comparable `copies` on the rolls that matter (§3.2)."""
    same = [copy for copy in copies if comparable(new, copy)]
    relations = tuple(_relation(new, copy, matters) for copy in same)
    lines = []
    for spec in matters:
        mine = _read(new, spec)
        theirs = [value for copy in same if (value := _read(copy, spec)) is not None]
        if mine is not None and theirs:
            lines.append(f'{spec.label} {mine} vs {", ".join(str(v) for v in sorted(theirs))}')
    won = bool(same) and all(relation in ('better', 'mixed-better') for relation in relations)
    return Comparison(won, len(same), tuple(lines), relations)


class CollectionCopies:
    """The owned copies from the collection database, read-only (macros/copies.py `owned_copies`: open placements,
    less the playing character's inventory and cube, offline characters own nothing). None when the item has no read,
    no match rule or the collection cannot be read (S8)."""

    def copies(self, facts: ItemFacts) -> list[ItemFacts] | None:
        if facts.observation is None:
            return None
        from inventory_tracking.macros.copies import owned_copies  # the macros import the loot layers

        found = owned_copies(dict(facts.observation))
        if found is None:
            return None
        return [from_observation(copy, where=Where.STASH, owner=Owner.PLAYER) for copy in found]
