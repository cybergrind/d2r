"""Layer 3 of the loot design (loot/design.md §3.4): what to do with one of the loop's items. Pure.

`decide(facts, value, owned)` applies the rules in order; the first that applies decides:

- K0 not the loop's (the player's, a print match, unknown): NEVER_TOUCH (S1)
- K1 a never-sell class: runes, gems, potions, set/unique and sunder charms KEEP; the loop's tomes, keys and cube
  NEVER_TOUCH (S2)
- K2 unidentified magic or better: IDENTIFY, never dropped unidentified (S8)
- K3 an always-keep want (the BiS rows of loot/data/wants.json): KEEP, duplicates included
- K4 a unique or set with no comparable owned copy, or owned copies that cannot be told: KEEP (S3, S8)
- K7 a charm or jewel (used in multiples, appraisal/owned.py MULTIPLE_COPY_BASES): KEEP when worth KEEP_IST or a want
  names it, else DROP; never compared as copies
- K5 worth DUPLICATE_IST or more by its own rolls: KEEP (expensive: duplicates kept, N1)
- K8 worthless (vendor, or under KEEP_IST) and no want: DROP
- K6 owned copies exist: KEEP only when better than every copy on the rolls that matter, else DROP (N2)
- K9 no price, no want: KEEP the first, logged `unknown` for the update-kb skill (Q13)
- K10 else KEEP: a cheap first copy, or a want

K7 runs before K5 and K8 before K6 (the design's table lists them the other way): a charm is never judged as a
duplicate, and a worthless item is not "cheap", so a better worthless copy is still dropped. DROP is the decision;
whether a carried DROP is sold at Jamella or put down is the town routine's (Q4).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.loot.facts import MAGIC, SET, UNIQUE, ItemFacts, Owner
from inventory_tracking.loot.value import DUPLICATE_IST, KEEP_IST, Comparison, Value, better_than, comparable, score


__all__ = [
    'CHARMS',
    'DECIDED_WITHOUT_COPIES',
    'GEMS',
    'JEWELS',
    'LOOP_GEAR',
    'POTIONS',
    'RULES',
    'RUNES',
    'SHADOW',
    'SUNDER',
    'Action',
    'Decision',
    'KeepRules',
    'decide',
    'decide_all',
]

# Shadow mode, M1 (the player, 2026-10-20 ~09:33: "start M0+M1"): every town visit and ground look logs the new
# decision beside the old one; nothing the loop does changes. False: no shadow lines
SHADOW = True

# Item types (itemtypes codes of items/metadata.py; the tests check them against macros/pickmode.py and the data)
RUNES = frozenset(('rune',))
GEMS = frozenset(('gema', 'gemd', 'geme', 'gemr', 'gems', 'gemt', 'gemz'))
CHARMS = frozenset(('scha', 'mcha', 'lcha'))
SUNDER = frozenset(('csch',))  # the Crafted Sunder Charm
JEWELS = frozenset(('jewl', 'cjwl'))
POTIONS = frozenset(('hpot', 'mpot', 'rpot', 'spot', 'apot', 'wpot', 'tpot', 'elix'))
ORGANS = frozenset(('body',))  # the Uber keys' organs
LOOP_GEAR = frozenset(('book', 'key', 'ques', 'scro'))  # Tomes, keys, scrolls, the Horadric Cube: the loop's tools
MULTIPLES = CHARMS | JEWELS


class Action(StrEnum):
    KEEP = 'keep'  # stash it
    IDENTIFY = 'identify'  # its value needs the identified read: a scroll in the field, Cain in town
    DROP = 'drop'  # the loop's item that fails: put down (field) or sold (already in town, Q4)
    SELL = 'sell'  # today's town path only (loot/today.py)
    NEVER_TOUCH = 'never-touch'  # the player's (S1), or the loop's own tools: kept as is


GIVE_UP = frozenset((Action.DROP, Action.SELL))


@dataclass(frozen=True)
class Decision:
    action: Action
    rule: str  # 'K6'
    reason: str  # for the log and the HUD
    compared: Comparison | None = None

    @property
    def gives_up(self) -> bool:
        return self.action in GIVE_UP

    def said(self) -> str:
        return f'{self.action.value} {self.rule} {self.reason}'.rstrip()


@dataclass(frozen=True)
class KeepRules:
    duplicate_ist: float = DUPLICATE_IST
    keep_ist: float = KEEP_IST


RULES = KeepRules()
# The rules decided without the owned copies: `decide_all` reads the collection only for the others
DECIDED_WITHOUT_COPIES = frozenset(('K0', 'K1', 'K2', 'K3', 'K5', 'K7', 'K8'))


def _price(value: Value) -> str:
    return f'{value.worth_ist:.3g} Ist' if value.worth_ist is not None else 'no price'


def decide(facts: ItemFacts, value: Value, owned: Sequence[ItemFacts] | None, rules: KeepRules = RULES) -> Decision:
    """The decision on one item (the module text); `owned`: its owned copies, None when they cannot be told."""
    if facts.owner != Owner.LOOP:
        return Decision(Action.NEVER_TOUCH, 'K0', f"the {facts.owner.value} owner's, not the loop's")
    kind = facts.base_type
    if kind in LOOP_GEAR:
        return Decision(Action.NEVER_TOUCH, 'K1', "the loop's own tool")
    if kind in RUNES | GEMS | POTIONS | ORGANS | SUNDER or (kind in CHARMS and facts.quality in (SET, UNIQUE)):
        return Decision(Action.KEEP, 'K1', 'never sold (runes, gems, potions, set/unique charms)')
    if not facts.identified and facts.quality >= MAGIC:
        return Decision(Action.IDENTIFY, 'K2', 'unidentified: never given up unread')
    keepers = [want for want in value.wants if want.always_keep]
    if keepers:
        return Decision(Action.KEEP, 'K3', f'always kept: {keepers[0].label}')
    named = facts.quality in (SET, UNIQUE)
    same = [copy for copy in owned if comparable(facts, copy)] if owned is not None else None
    if named and not same:
        why = 'owned copies cannot be told' if same is None else 'the first copy'
        return Decision(Action.KEEP, 'K4', f'{why} ({_price(value)})')
    wanted = f'; wanted: {value.wants[0].label}' if value.wants else ''
    if kind in MULTIPLES:
        if value.wants or (value.tier != 'worthless' and (value.worth_ist or 0) >= rules.keep_ist):
            return Decision(Action.KEEP, 'K7', f'used in multiples, {_price(value)}{wanted}')
        return Decision(Action.DROP, 'K7', f'used in multiples, worthless ({value.said()})')
    if value.worth_ist is not None and value.worth_ist >= rules.duplicate_ist:
        return Decision(Action.KEEP, 'K5', f'expensive: {_price(value)} by its rolls')
    if value.tier == 'worthless' and not value.wants:
        return Decision(Action.DROP, 'K8', f'worthless ({value.said()}), no want')
    if same:
        compared = better_than(facts, same, value.matters)
        told = f'{len(same)} owned: {compared.said()}'
        if compared.better:
            return Decision(Action.KEEP, 'K6', f'cheap ({_price(value)}), better than the {told}', compared)
        return Decision(Action.DROP, 'K6', f'cheap ({_price(value)}), not better than the {told}', compared)
    if value.tier == 'unknown' and not value.wants:
        return Decision(Action.KEEP, 'K9', 'unknown: no price, the first kept (for the update-kb skill)')
    return Decision(Action.KEEP, 'K10', f'{value.tier} ({_price(value)}), no comparable owned copy{wanted}')


def decide_all(
    items: Sequence[tuple[ItemFacts, Value]],
    copies: Callable[[ItemFacts], Sequence[ItemFacts] | None],
    rules: KeepRules = RULES,
) -> list[tuple[ItemFacts, Value, Decision]]:
    """The decisions on several items carried at once, the best rolled first, so that the first of two copies kept
    in the same visit counts as owned for the second (§2.1 `items`, §6.2 `two_copies_in_one_visit_best_first`).
    `copies` is asked only for the items whose rule needs them."""
    order = sorted(items, key=lambda pair: -score(pair[0], pair[1].matters))
    held: list[ItemFacts] = []
    found = []
    for facts, value in order:
        decision = decide(facts, value, None, rules)
        if decision.rule not in DECIDED_WITHOUT_COPIES:
            owned = copies(facts)
            if owned is not None:
                owned = [*owned, *(copy for copy in held if comparable(facts, copy))]
            decision = decide(facts, value, owned, rules)
        if decision.action == Action.KEEP:
            held.append(facts)
        found.append((facts, value, decision))
    return found
