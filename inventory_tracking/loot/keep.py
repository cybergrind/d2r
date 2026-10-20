"""Layer 3 of the loot design (loot/design.md §3.4): what to do with one of the loop's items. Pure.

`decide(facts, value, owned)` applies the rules in order; the first that applies decides:

- K0 not the loop's (the player's, a print match, unknown): NEVER_TOUCH (S1)
- K1 a never-sell class: runes, gems, potions, set/unique and sunder charms, Wirt's Leg KEEP; the loop's tomes, keys,
  cube and the quest items (Worldstone Shards, statues, Uber keys, essences: itemtype `ques`) NEVER_TOUCH (S2)
- K2 unidentified magic or better: IDENTIFY, never dropped unidentified (S8)
- K3 an always-keep want (the BiS rows of loot/data/wants.json): KEEP, duplicates included; after K5, a want with
  `keep_up_to` (the Spirit base Monarch, 2026-10-20 ~12:50): KEEP while fewer comparable copies are owned, then by
  the rules below (K6: only a better copy)
- K4 a unique or set with no comparable owned copy, or owned copies that cannot be told: KEEP (S3, S8); but with
  FIRST_COPY_USABLE_ONLY a told first copy no build the player may play names (`unusable_first`: no want row, the
  usable rows included; priced under DUPLICATE_IST; appraised vendor or slow; no charm or jewel): DROP
- K7 a charm or jewel (used in multiples, appraisal/owned.py MULTIPLE_COPY_BASES): KEEP when worth KEEP_IST, a want
  names it or it has no price (S8), else DROP; never compared as copies
- K5 worth DUPLICATE_IST or more by its own rolls: KEEP (expensive: duplicates kept, N1)
- K8 worthless (vendor, or under KEEP_IST) and no want: DROP; and a rare circlet or helm no want row names
  (JUNK_UNWANTED: the player, 2026-10-20 ~12:50, rare helms kept only when "really good"), priced or not; rare boots
  and belts the same (~19:25: "we can keep really good ones"); and magic gloves no want row names (JUNK_MAGIC, ~13:30:
  the IAS + skills gloves are the rows)
- K6 owned copies exist: KEEP only when better than every copy on the rolls that matter, else DROP (N2)
- K9 no price, no want: KEEP the first, logged `unknown` for the update-kb skill (Q13)
- K10 else KEEP: a cheap first copy, or a want

K7 runs before K5 and K8 before K6 (the design's table lists them the other way): a charm is never judged as a
duplicate, and a worthless item is not "cheap", so a better worthless copy is still dropped; but not a set or unique
copy better than every owned one (K6 first for them, 2026-10-20 ~17:10: the 2026-10-18 best-copy ruling). DROP is
the decision; whether a carried DROP is sold at Jamella or put down is the town routine's (Q4).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.loot.facts import MAGIC, RARE, SET, UNIQUE, ItemFacts, Owner
from inventory_tracking.loot.value import DUPLICATE_IST, KEEP_IST, Comparison, Value, better_than, comparable, score


__all__ = [
    'CHARMS',
    'DECIDED_WITHOUT_COPIES',
    'DECIDES',
    'FIRST_COPY_SELLS_OVER',
    'FIRST_COPY_SETS',
    'FIRST_COPY_USABLE_ONLY',
    'GEMS',
    'JEWELS',
    'JUNK_MAGIC',
    'JUNK_UNWANTED',
    'LOOP_GEAR',
    'NEVER_SOLD_CODES',
    'POTIONS',
    'RULES',
    'RUNES',
    'SHADOW',
    'SUNDER',
    'TOWN_DECIDES',
    'Action',
    'Decision',
    'KeepRules',
    'decide',
    'decide_all',
    'unusable_first',
]

# Shadow mode, M1 (the player, 2026-10-20 ~09:33: "start M0+M1"): every town visit and ground look logs the new
# decision beside the old one; nothing the loop does changes. False: no shadow lines
SHADOW = True
# M2, the town side (loot/design.md §7; the player, 2026-10-20 ~15:05, answering: "Sell cheap duplicates"): a set or
# unique copy `decide` gives up (K6: under 1 Ist, not better than an owned copy, no want row) is sold at the visit
# instead of stashed (loot/api.py `sold_copies`, macros/visit.py). False: the visit sells what today's rules sell.
# On 2026-10-20 ~16:35 after the review: today's replay would have sold only The Reaper's Toll (0.653 Ist, 1 owned)
DECIDES = True
# M6, one town decision (loot/design.md §7, §9 "M6"; the player, 2026-10-20 16:55: "can you check if we're using the
# shared code across different activities to control pickups and what to keep?", then "go ahead with the merge
# agent"): the town visit's junk is what `decide` gives up for every loop item, the same rules the field uses, under
# the town's guards (loot/api.py `town_verdicts`: the player's items, runes, gems, potions, set/unique charms, shards,
# keys, tomes and the cube never; the best copy kept; unknown kept; nothing appraised other than vendor sold but by a
# dated rule). False: today's chain (junk.py `junk_of`, copies.py `sold`, the M2 copies) decides and the shadow logs
# the unified decision beside it (`Macro: loot: shadow: town merge: ...`). On 2026-10-20 ~18:45 (the player: "switch on
# new rules"), after 3 visits of the shadow with 0 differ
TOWN_DECIDES = True
# The first copy of a set or unique item is kept only when a build the player may play names it (the player,
# 2026-10-20 ~20:10, after Skullder's Ire 0.84 Ist and Corpsemourn 0.48 Ist were stashed: "ok, let's probably keep only
# uniques that are mentioned in guides as something that I probably could use"; ~20:17: "we shouldn't limit to just
# warlock's guide. actually I'd like to try paladin, sorc, barb, necro, traps and amazon builds"): the `usable` rows of
# loot/data/wants.json (loot/build_wants.py `usable_rows`) and every other want row spare it; else a priced first copy
# under DUPLICATE_IST appraised FIRST_COPY_SELLS_OVER is given up (K4 DROP: sold in town, put down by the field's G18
# step). No price, unread copies, expensive, wanted: kept as before. False: every first copy kept (K4)
FIRST_COPY_USABLE_ONLY = True
# Sets too (the coordinator's reading, 2026-10-20 ~20:10: the player's complaint included a Tal Rasha's belt). False:
# the first copy of a set item is kept as before
FIRST_COPY_SETS = True
# The verdicts a first copy is given up over: `self`, `sell`, `check` and `keep` stay kept until the player rules
FIRST_COPY_SELLS_OVER = frozenset(('vendor', 'slow'))

# Item types (itemtypes codes of items/metadata.py; the tests check them against macros/pickmode.py and the data)
RUNES = frozenset(('rune',))
GEMS = frozenset(('gema', 'gemd', 'geme', 'gemr', 'gems', 'gemt', 'gemz'))
CHARMS = frozenset(('scha', 'mcha', 'lcha'))
SUNDER = frozenset(('csch',))  # the Crafted Sunder Charm
JEWELS = frozenset(('jewl', 'cjwl'))
POTIONS = frozenset(('hpot', 'mpot', 'rpot', 'spot', 'apot', 'wpot', 'tpot', 'elix'))
ORGANS = frozenset(('body',))  # the Uber keys' organs
LOOP_GEAR = frozenset(('book', 'key', 'ques', 'scro'))  # Tomes, keys, scrolls, the Horadric Cube: the loop's tools
# Kept whatever a price says, by items.txt code (third-parties/d2data/json/weapons.json:20402 `leg`, itemtype club):
# Wirt's Leg, the way to the cow level, carried one at a time (loot/materials.py CARRY_ONE). The Worldstone Shards
# (misc.json:12513 `xa1` ... `xa5`), statues, Uber keys and essences are itemtype `ques`: LOOP_GEAR above
NEVER_SOLD_CODES = frozenset(('leg',))
MULTIPLES = CHARMS | JEWELS
# The rare item types kept only by a want row (the player, 2026-10-20 ~12:50: "rare helms (tiara, corona, etc) that are
# really good - fcr + 2skills level + other valuable stats"; the rows: loot/build_wants.py G10): circlets, and plain
# helms, which roll neither FCR nor a Warlock skill (d2data magicsuffix/magicprefix itypes). Anything else of them that
# is not worth DUPLICATE_IST by its own rolls (K5) is junk, dropped in the field (loot/api.py `droppable` still spares
# 1 Ist or more). Rare boots and belts too (the player, 2026-10-20 ~19:25, on rare boots and belts: "we can keep really
# good ones"; the rows: loot/build_wants.py G21, G22)
JUNK_UNWANTED = frozenset(('circ', 'helm', 'boot', 'belt'))
JUNK_NAMES = {'circ': 'circlet', 'helm': 'helm', 'boot': 'boot', 'belt': 'belt'}  # for the log
# The magic item types kept only by a want row or a price of DUPLICATE_IST by their own rolls (K5): gloves (the player,
# 2026-10-20 ~13:30: "identify magic gloves that can roll something like 40ias + annother valuable roll, like skills";
# guides/pricing.html:203: "+3 skills without IAS, or IAS alone = vendor; +2 Passive and Magic or +2 Bow of Alacrity =
# vendor"; the rows: loot/build_wants.py G19). Anything else of them is junk, dropped in the field
JUNK_MAGIC = frozenset(('glov',))


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


def unusable_first(facts: ItemFacts, value: Value, rules: KeepRules = RULES) -> str | None:
    """Why the loop's set or unique item `facts`, with no comparable owned copy, is given up (FIRST_COPY_USABLE_ONLY),
    None when it is kept: a unique (or a set item, FIRST_COPY_SETS) of no charm or jewel kind, no want row names it
    (the usable rows included), priced under DUPLICATE_IST by its own rolls and appraised FIRST_COPY_SELLS_OVER.
    Pure."""
    if not FIRST_COPY_USABLE_ONLY or facts.owner != Owner.LOOP or not facts.identified:
        return None
    if facts.quality != UNIQUE and not (facts.quality == SET and FIRST_COPY_SETS):
        return None
    if facts.base_type in MULTIPLES or value.wants or value.verdict not in FIRST_COPY_SELLS_OVER:
        return None
    if value.worth_ist is None or value.worth_ist >= rules.duplicate_ist:
        return None
    return f'the first copy, no build names it ({_price(value)}, {value.verdict})'


def decide(facts: ItemFacts, value: Value, owned: Sequence[ItemFacts] | None, rules: KeepRules = RULES) -> Decision:
    """The decision on one item (the module text); `owned`: its owned copies, None when they cannot be told."""
    if facts.owner != Owner.LOOP:
        return Decision(Action.NEVER_TOUCH, 'K0', f"the {facts.owner.value} owner's, not the loop's")
    kind = facts.base_type
    if kind in LOOP_GEAR:
        return Decision(Action.NEVER_TOUCH, 'K1', "the loop's own tool")
    if kind in RUNES | GEMS | POTIONS | ORGANS | SUNDER or (kind in CHARMS and facts.quality in (SET, UNIQUE)):
        return Decision(Action.KEEP, 'K1', 'never sold (runes, gems, potions, set/unique charms)')
    if facts.code in NEVER_SOLD_CODES:
        return Decision(Action.KEEP, 'K1', "never sold (Wirt's Leg)")
    if not facts.identified and facts.quality >= MAGIC:
        return Decision(Action.IDENTIFY, 'K2', 'unidentified: never given up unread')
    keepers = [want for want in value.wants if want.always_keep]
    if keepers:
        return Decision(Action.KEEP, 'K3', f'always kept: {keepers[0].label}')
    named = facts.quality in (SET, UNIQUE)
    same = [copy for copy in owned if comparable(facts, copy)] if owned is not None else None
    if named and not same:
        if same is not None and (given_up := unusable_first(facts, value, rules)) is not None:
            return Decision(Action.DROP, 'K4', given_up)
        why = 'owned copies cannot be told' if same is None else 'the first copy'
        return Decision(Action.KEEP, 'K4', f'{why} ({_price(value)})')
    wanted = f'; wanted: {value.wants[0].label}' if value.wants else ''
    if kind in MULTIPLES:
        if value.wants or (value.tier != 'worthless' and (value.worth_ist or 0) >= rules.keep_ist):
            return Decision(Action.KEEP, 'K7', f'used in multiples, {_price(value)}{wanted}')
        if value.tier == 'unknown':
            # S8, "unknown is kept: no price -> keep, never sell or drop": no price read as 0 Ist dropped a magic Small
            # Charm with a `check` verdict and no band (13:30:27 on 2026-10-20, the shadow's town line)
            return Decision(Action.KEEP, 'K7', f'used in multiples, unknown: no price, kept (S8; {value.said()})')
        return Decision(Action.DROP, 'K7', f'used in multiples, worthless ({value.said()})')
    if value.worth_ist is not None and value.worth_ist >= rules.duplicate_ist:
        return Decision(Action.KEEP, 'K5', f'expensive: {_price(value)} by its rolls')
    capped = next((want for want in value.wants if want.keep_up_to is not None), None)
    if capped is not None and capped.keep_up_to is not None and same is not None and len(same) < capped.keep_up_to:
        return Decision(Action.KEEP, 'K3', f'{len(same)} owned, kept up to {capped.keep_up_to}: {capped.label}')
    if named and same and value.tier == 'worthless':
        # The best copy first ("loop should keep the best copy first", the player, 2026-10-18; N2): a set or unique
        # copy better than every owned one is kept even when worthless; the worse owned one is the mules skill's.
        # Demon Limb, 17:09:07 on 2026-10-20: ED 206 vs 200, fire res 18 vs 16, vendor 0.379 Ist, was K8 before
        compared = better_than(facts, same, value.matters)
        if compared.better:
            told = f'{len(same)} owned: {compared.said()}'
            return Decision(Action.KEEP, 'K6', f'the best copy ({value.said()}), better than the {told}', compared)
    if value.tier == 'worthless' and not value.wants:
        return Decision(Action.DROP, 'K8', f'worthless ({value.said()}), no want')
    if facts.quality == RARE and kind in JUNK_UNWANTED and not value.wants:
        return Decision(Action.DROP, 'K8', f'a rare {JUNK_NAMES[kind]} no want row names ({value.said()})')
    if facts.quality == MAGIC and kind in JUNK_MAGIC and not value.wants:
        return Decision(Action.DROP, 'K8', f'magic gloves no want row names ({value.said()})')
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
