"""Today's keep and pickup judgements in the loot layers' types (loot/design.md §7 M0): the acceptance table runs
against them to show which valuables today's code fails (tests/inventory_tracking/loot/test_valuables.py, the
strict xfails). Not on the loop's path.

- `decide`: the town visit's judgement as the live loop composes it: Cain's identify, the identify worker's
  verdict (no owned-copy lookup is wired: appraisal/service.py builds the IdentifyWorker without `owned=`, so
  identify/service.py `owned_verdict` never runs in the loop), junk.py `junk_of` (identified, `sellable`, `vendor`),
  the amulet keeper (engine.py `protected`) and copies.py `keep_copy` for a `vendor` set or unique.
- `judge`: the GOOD pickup level, pickmode.py `sure`, on the drop as the ground read gives it today (game/decode.py
  `rolled`: rolls only for game/layout.py ROLLED_TYPES, and of BASE_ROLLED_TYPES only for white and superior ones).
  Since M5 (2026-10-20) `sure` takes the white bases the ground read picks (pickmode.py `ground_base`).
"""

from collections.abc import Sequence

from inventory_tracking.game.layout import MAGIC_ROLLED_TYPES, ROLLED_QUALITIES, ROLLED_TYPES, WHITE_QUALITIES
from inventory_tracking.game.records import NAMED, VALUABLE, Carried, Drop, Rolls, prized
from inventory_tracking.loot.facts import MAGIC, SET, UNIQUE, ItemFacts, Owner
from inventory_tracking.loot.ground_judge import GroundVerdict, Then
from inventory_tracking.loot.keep import GEMS, RUNES, Action, Decision
from inventory_tracking.loot.value import Value
from inventory_tracking.macros.copies import Appraisal, keep_copy
from inventory_tracking.macros.junk import JUNK_QUALITIES, VENDOR
from inventory_tracking.macros.keepers import amulet_keeper
from inventory_tracking.macros.pickmode import sellable, sure


__all__ = ['carried', 'decide', 'drop', 'judge']


def carried(facts: ItemFacts) -> Carried:
    cell = facts.cell or (0, 0)
    return Carried(facts.unit_id, facts.txt or 0, cell[0], cell[1], facts.size, facts.quality, facts.identified,
                   facts.row or 0)  # fmt: skip


def _stats(facts: ItemFacts) -> dict[int, int]:
    found: dict[int, int] = {}
    for key, value in (facts.rolls or {}).items():
        stat = int(key.partition(':')[0])
        found[stat] = max(found.get(stat, value), value)
    return found


def decide(facts: ItemFacts, value: Value, owned: Sequence[ItemFacts] | None) -> Decision:
    """Today's town judgement (the module text)."""
    if facts.owner != Owner.LOOP:
        return Decision(Action.NEVER_TOUCH, 'today', "the player's (protected cell or print)")
    if not facts.identified and facts.quality >= MAGIC:
        return Decision(Action.IDENTIFY, 'today', 'identified at Cain')
    item = carried(facts)
    if why := amulet_keeper(item, _stats(facts)):
        return Decision(Action.KEEP, 'today', f'amulet keeper: {why}')
    if facts.quality not in JUNK_QUALITIES or not sellable(facts.base_type or None, facts.quality, facts.txt):
        return Decision(Action.KEEP, 'today', 'not sellable (junk.junk_of)')
    if value.verdict != VENDOR:
        return Decision(Action.KEEP, 'today', f'verdict {value.verdict}')
    if facts.quality in (SET, UNIQUE):
        observation = dict(facts.observation) if facts.observation is not None else None
        copies = [dict(c.observation) for c in owned if c.observation is not None] if owned is not None else None
        if why := keep_copy(item, Appraisal(VENDOR, observation), copies):
            return Decision(Action.KEEP, 'today', f'copies.keep_copy: {why}')
    return Decision(Action.SELL, 'today', 'vendor')


def drop(facts: ItemFacts) -> Drop:
    """The drop as today's look reads it: its source by kind, `prized` by the marks, rolls only for ROLLED_TYPES."""
    kind = facts.base_type
    source = (
        NAMED if facts.quality in (SET, UNIQUE)
        else 'rune' if kind in RUNES
        else 'material' if kind in GEMS
        else 'shown'
    )  # fmt: skip
    rolls = None
    read = kind in MAGIC_ROLLED_TYPES or facts.quality in WHITE_QUALITIES
    if kind in ROLLED_TYPES and read and facts.quality in ROLLED_QUALITIES and facts.rolls is not None:
        found = _stats(facts)
        skills = tuple((int(k.partition(':')[2]), v) for k, v in facts.rolls.items() if k.startswith('107:'))
        tabs = tuple((int(k.partition(':')[2]), v) for k, v in facts.rolls.items() if k.startswith('188:'))
        rolls = Rolls(facts.sockets or 0, skills, found.get(16, 0), min(found.get(s, 0) for s in (39, 41, 43, 45)),
                      bool(facts.ethereal), found.get(17, 0), tabs)  # fmt: skip
    return Drop(facts.unit_id, 0.0, 0.0, facts.base_name, VALUABLE, facts.size, prized(source, marked=facts.marked),
                source, facts.txt or 0, facts.quality, rolls)  # fmt: skip


def judge(facts: ItemFacts) -> GroundVerdict:
    """Today's GOOD pickup (pickmode.py `sure`) in a ground verdict."""
    if sure(drop(facts)):
        return GroundVerdict(True, False, Then.KEEP if facts.identified else Then.IDENTIFY, 'today', 'pickmode.sure')
    return GroundVerdict(False, False, None, '', 'pickmode.sure leaves it')
