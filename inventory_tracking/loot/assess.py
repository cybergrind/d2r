"""One entry point for every item judgement (loot/design.md §10). The player, 2026-10-23: "we need to have one
dedicated place where all assessments are happening - reuse it everywhere - single entry point - easy to test", then
"ok, let's unify everything into a single way to do assessments and this will be our starting point".

`Assessor(appraiser, copies, counted).assess(facts, site)` answers an `Assessment`: what the item is worth (`value`),
what to do with it at that site (`outcome`), the rule that decided (`rule`) and one `why`. `assess_all` judges the
items carried at once, as the town does (the best rolled first: the first of two copies kept counts as owned for the
second). It composes the pure loot layers and forks none of their rules:

- GROUND, pick or leave a drop: the plain-base allowlist (base_floor.py `allowed`), else ground_judge.py `judge`; a
  magic or rare item that is no sure valuable is the field identify's (`Assessment.field`: api.py CLASSES, else the
  big classes G14 / G15 by size), left when no field class takes it; whatever the loot marks point at is picked (D7)
- FIELD, after the Tome, keep or put down: keep.py `decide_all`, then api.py `droppable`; an unidentified magic amulet
  waits for Cain (api.py RINGS_TO_CAIN, rule CAIN), any other the Tome (K2)
- TOWN, GAMBLE, keep (stash) or sell to a vendor: api.py `town_verdicts` (`decide_all` under `town_kept`)
- CARD, CORPUS, the Alt+D / identify card's or a replay's verdict and why: TOWN on the one item, judged as the loop's
- SHOP, a buy target or not: the priced triage verdict (shop/service.py `priced`) and the reviewed patterns
  (shop/rules.py `match_item`)

Last comes one guard over every site (`never_trash`): the player's items, an unidentified one, runes, gems, set/unique
charms (a low Gheed's Fortune aside, keep.py GHEEDS_BY_ROLL), the Sunder, organs, the loop's tools, Wirt's Leg, an
always-kept want row and anything worth DUPLICATE_IST by its own rolls are never given up (the player: "we absolutely
MUST NOT trash good items"; "never sell runes, gems, set/unique charms, the player's own items"). The composed rules
already keep them, so it never fires; if it does, the item is kept and the why names the rule that tried.

Price sources (loot/value.py `Appraiser`): `BookAppraiser` (live: the identify worker's KB results by unit id,
loot/shadow.py BOOK), `ResultAppraiser` (a retrieve callable: the identify worker's appraisal/retrieval.py `detail`, the
shop's triage; its verdict the identify worker's by default, `identify_verdict`), `FakeAppraiser` (a table, for tests).
This module imports nothing of pricing/: the callers wire the engines into a price source. Pure but for the price
source, the owned copies and the switches read at call time.

The outcome words: VENDOR is "sold to a vendor" (junk), never the triage's `sell` ("trade it": a value), which a card
showing both would confuse (rca/2026-10-23/assess-sites-findings.md R3).

Not decided here; each stays with its caller, and phase 2 keeps it there (rca/2026-10-23/assess-sites-findings.md):

- engine.py `protected` (D3): the player's item by its print, an amulet whose stats are unread, a Worldstone Shard the
  game can still use. It guards every action (the visit's sale and put-down, cube.py `drop_item`, gamble.py `_sell`)
  after any decision, this module's included: an Assessment never licenses an action on its own.
- The Gheed's swap's magic-find compare (D8, macros/charms.py `choose`): the better of the new and the player's charm
  is carried, a low new one put down; keep.py K1 judges one charm alone.
- The pickup level MOST (D9, macros/pickmode.py `_taken`): everything the filter shows; GROUND is the GOOD level's
  judgement.
- The guard's identify candidates (D10, macros/pickmode.py `is_candidate`, lootpolicy.py): which drops hold the game.
  It is not "a pick that is no must-have": an allowlisted base that is no must-have row still holds the game.
- The visit's stock rules (R2): surplus flawless gems sold when the stacks are full (loot/storage.py `surplus`),
  full-stack materials put down (macros/visit.py `_material`, town.py `sold_full`), the loop's spare potions put down
  (visit.py `_potions_down`). `never_trash` would refuse each as a judgement; they are storage rules.
- The loop-off identify picks (R4, api.py `Field.takes`): GROUND names the class of an IDENTIFY pick; whether it is
  taken now (the KP_6 loop on, api.py FIELD_IDENTIFY and CLASSES, room, the Tome) is the field identify's.
- The full-stack runes and materials not picked with the loop on (R5, running/valuables.py `_picked`).
- Also the site's: supplies (gold, potions), where an item goes (storage.py), the walk, Jamella or a put-down.

Phase 1 (2026-10-23): nothing live called this module. Phase 2A (2026-10-23, the player: "go ahead. I want to have one
place that decides pickups/value"): the ground pickup (macros/pickmode.py ASSESS_GROUND) and the field routine (api.py
ASSESS_FIELD) call it; each logs the old decision beside the new one when they differ (`shadow`, design.md §10.4).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import cache
from typing import Any, Protocol

from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL
from inventory_tracking.game.records import Carried
from inventory_tracking.loot import api as loot_api, base_floor, ground_judge, shadow as loot_shadow
from inventory_tracking.loot.api import TownVerdict, droppable, town_verdicts
from inventory_tracking.loot.facts import MAGIC, QUALITY_NAMES, RARE, SET, UNIQUE, ItemFacts, Owner, from_carried
from inventory_tracking.loot.ground_judge import GroundVerdict, OwnedCount, Then
from inventory_tracking.loot.keep import (
    CHARMS,
    GEMS,
    JEWELS,
    LOOP_GEAR,
    NEVER_SOLD_CODES,
    ORGANS,
    POTIONS,
    RUNES,
    SUNDER,
    Action,
    Decision,
    decide_all,
    gheeds_low,
)
from inventory_tracking.loot.materials import CARRY_ONE
from inventory_tracking.loot.shadow import Appraised
from inventory_tracking.loot.value import (
    DUPLICATE_IST,
    Appraiser,
    Band,
    OwnedCopies,
    Value,
    appraise_result,
    assess as valued,
)


__all__ = [
    'CAIN',
    'GIVE_UP',
    'GUARD',
    'NEVER_TRASH',
    'NO_COPIES',
    'NO_LOOK',
    'NO_PRICES',
    'S8',
    'SHADOW',
    'Assessment',
    'Assessor',
    'BookAppraiser',
    'CalledCopies',
    'FakeAppraiser',
    'Look',
    'NoCopies',
    'Outcome',
    'Price',
    'ResultAppraiser',
    'Site',
    'TableCopies',
    'carried_facts',
    'identify_verdict',
    'live',
    'never_trash',
    'shadow',
    'shop_priced',
    'triage_verdict',
]


class Site(StrEnum):
    GROUND = 'ground'  # a drop in the look: pick it up or leave it
    FIELD = 'field'  # one of the loop's items after the Tome's identify: keep it or put it down at the feet
    TOWN = 'town'  # the loop's carried items at a visit: stash or sell
    GAMBLE = 'gamble'  # a gambled item: the town's rules
    SHOP = 'shop'  # a vendor's stock item: a buy target or not
    CARD = 'card'  # the Alt+D / identify HUD card: its verdict and why, as the loop would judge it
    CORPUS = 'corpus'  # a recorded read replayed: the card's judgement, no live state


class Outcome(StrEnum):
    PICK = 'pick'
    LEAVE = 'leave'
    KEEP = 'keep'
    IDENTIFY = 'identify'  # its value needs the identified read: the Tome in the field, Cain in town
    NEVER_TOUCH = 'never-touch'  # the player's, or the loop's own tools: kept as is
    DROP = 'drop'  # put down at the feet (field)
    # Sold to a vendor (town, gamble; the card: the town would). Not 'sell', the triage's trade verdict (R3, 2026-10-23)
    VENDOR = 'vendor'
    BUY = 'buy'
    PASS = 'pass'


GIVE_UP = frozenset((Outcome.LEAVE, Outcome.DROP, Outcome.VENDOR))  # the outcomes that lose an item
TOWN_SITES = frozenset((Site.TOWN, Site.GAMBLE, Site.CARD, Site.CORPUS))
AS_THE_LOOPS = frozenset((Site.CARD, Site.CORPUS))  # judged as the loop's item: what the loop would do with it
S8 = 'S8'  # no appraisal or no identified read: kept (loot/design.md §0 S8)
GUARD = 'guard'  # a site's guard (api.py `droppable`, `town_kept`) kept what the keep rules gave up
NEVER_TRASH = 'never-trash'  # the last guard (`never_trash`) kept it
CAIN = 'Cain'  # FIELD: an unidentified magic amulet carried to Cain unidentified (api.py RINGS_TO_CAIN)
ACTIONS = {
    Action.KEEP: Outcome.KEEP,
    Action.IDENTIFY: Outcome.IDENTIFY,
    Action.NEVER_TOUCH: Outcome.NEVER_TOUCH,
    Action.DROP: Outcome.DROP,
    Action.SELL: Outcome.VENDOR,
}
# Never given up anywhere (S1, S2; keep.py K1, api.py NEVER_DROPPED / TOWN_NEVER_SOLD)
NEVER_GIVEN_UP = RUNES | GEMS | SUNDER | ORGANS | POTIONS | LOOP_GEAR
ALWAYS_PICKED = RUNES | GEMS | SUNDER | CHARMS | JEWELS  # ground_judge.py G1
PLAIN_LEFT = 'on no allowlist entry (loot/data/base-pickups.json, 4+ Ist)'
JEWELRY = frozenset(('ring', 'amul'))  # itemtypes codes (api.py NAMED_SMALL)
# The ring and amulet qualities the ground takes whatever the field (pickmode.py `sure`, 2026-10-17 "rare amulets - also
# pickup"): Cain or the town decides them, never the field's gate
JEWELRY_SURE = frozenset((RARE, SET, UNIQUE))


@dataclass(frozen=True)
class Assessment:
    """One item judged at one site: what it is, what it is worth, what to do and why."""

    facts: ItemFacts
    site: Site
    outcome: Outcome
    rule: str  # 'K6', 'G8', 'S8', GUARD, NEVER_TRASH, 'allowlist', 'shop'
    why: str
    value: Value | None = None
    decision: Decision | None = None  # keep.py's (field, town, gamble, card, corpus)
    ground: GroundVerdict | None = None  # the ground's
    guard: str | None = None  # why a guard kept what the rules gave up
    # GROUND (2026-10-23, phase 2A): the field identify's class for a magic or rare drop (api.py CLASSES, else G14 / G15
    # by size; what api.py `Field.takes` names, the loop aside), None for none; `for_field`: the pick is only the
    # field's, so the caller takes it only through the field's gate (the KP_6 loop on, room: R4); `plain`: a plain
    # base judged by the allowlist, the same answer in every pickup level
    field: str | None = None
    for_field: bool = False
    plain: bool = False

    @property
    def gives_up(self) -> bool:
        """Whether the item is lost: left on the ground, put down or sold."""
        return self.outcome in GIVE_UP

    @property
    def sure(self) -> bool:
        """GROUND: picked whatever the field's gate (the GOOD level's sure valuables, every plain base allowlisted)."""
        return self.outcome == Outcome.PICK and not self.for_field

    def said(self) -> str:
        """'Goblin Toe (Light Plated Boots): town: sell K6 cheap (0.65 Ist), not better than the 2 owned: ...'."""
        return f'{self.facts.title()}: {self.site.value}: {self.outcome.value} {self.rule} {self.why}'.rstrip()


# -- price sources -----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Price:
    """A table row of `FakeAppraiser`: the price by the item's rolls, the appraisal's verdict, the asks' band."""

    worth: float | None
    verdict: str | None = None
    band: Band | None = None


class FakeAppraiser:
    """Prices from a table, keyed by unit id, else name, else items.txt code (tests: no knowledge base loaded). A row
    that is a `Price` becomes a `Value` by loot/value.py `assess` (its wants and rolls from the facts); None or no row:
    no appraisal (S8)."""

    def __init__(self, prices: Mapping[int | str, Price | Value | None], default: Price | None = None) -> None:
        self.prices, self.default = prices, default

    def appraise(self, facts: ItemFacts) -> Value | None:
        found = next((self.prices[key] for key in (facts.unit_id, facts.name, facts.code) if key in self.prices),
                     self.default)  # fmt: skip
        if found is None or isinstance(found, Value):
            return found
        return valued(facts, worth=found.worth, verdict=found.verdict, band=found.band)


class Reads(Protocol):
    """Appraisals by unit id: loot/shadow.py `Book`, or the field routine's `FieldHands.appraise` mapping."""

    def get(self, unit_id: int, /) -> Appraised | None: ...


class NoPrices:
    """No price source: what judges without a price (the ground, an unidentified item in the field; S8 elsewhere)."""

    def appraise(self, facts: ItemFacts) -> Value | None:
        del facts
        return None


NO_PRICES = NoPrices()


class BookAppraiser:
    """Live: the identify worker's appraisals by unit id (loot/shadow.py BOOK; IdentifyWorker `_assess` / `appraise`
    note each read, KB result and verdict; the field routine's `FieldHands.appraise`). A plain base with none is judged
    by its facts alone (api.py `town_sold`: keep.py K9 and the allowlist need no price). Else None (S8)."""

    def __init__(self, book: Reads | None = None) -> None:
        self.book = loot_shadow.BOOK if book is None else book  # BOOK read at the call (tests swap it)

    def appraise(self, facts: ItemFacts) -> Value | None:
        entry = self.book.get(facts.unit_id)
        if entry is not None:
            return appraise_result(facts, entry.result, entry.verdict)
        if base_floor.is_plain(facts.code, facts.quality):
            return valued(facts, worth=None)
        return None


class ResultAppraiser:
    """A KB lookup per read: `retrieve(observation)` gives the KB result (the identify worker's process over
    appraisal/retrieval.py `detail`, the shop's triage), `verdict(result, observation)` the verdict it is judged with:
    by default the identify worker's (`identify_verdict`: what BOOK holds live, its leveling override included, D4);
    `triage_verdict` for the triage's own (the shop). No read, no result or a failed lookup: None (S8, logged)."""

    def __init__(
        self,
        retrieve: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
        verdict: Callable[[Mapping[str, Any], Mapping[str, Any]], str | None] | None = None,
    ) -> None:
        self.retrieve = retrieve
        self.verdict = identify_verdict if verdict is None else verdict

    def appraise(self, facts: ItemFacts) -> Value | None:
        if facts.observation is None:
            return None
        try:
            result = self.retrieve(facts.observation)
            if result is None:
                return None
            verdict = self.verdict(result, facts.observation)
        except Exception as error:  # S8: no appraisal, kept
            LOG.info('Loot: assess: no appraisal of %s (%s): kept (S8)', facts.title(), error)
            return None
        return appraise_result(facts, result, verdict)


def identify_verdict(result: Mapping[str, Any], observation: Mapping[str, Any]) -> str | None:
    """The identify worker's verdict on a KB result (identify/service.py `verdict_for` with no owned copies, as the
    live worker is built: appraisal/service.py), the one BOOK holds: the triage's verdict, a leveling use turning a
    vendor or slow one into check (identify/service.py `assessed_verdict`; the findings' D4)."""
    from inventory_tracking.identify.service import verdict_for  # here: the identify worker's imports are heavy

    return verdict_for(result, None, observation)[0]


def triage_verdict(result: Mapping[str, Any], observation: Mapping[str, Any]) -> str | None:
    """No verdict of its own: loot/value.py `appraise_result` takes the triage's (the shop's `priced` reads it)."""
    del result, observation
    return None


def carried_facts(item: Carried, owner: Owner, book: Reads | None = None) -> ItemFacts:
    """A carried item's facts from the identify worker's read of it when there is one (what api.py `town_sold`,
    gamble.py `keep_rules` and api.py `Field._judge` build), else its class and quality."""
    entry = (loot_shadow.BOOK if book is None else book).get(item.unit_id)
    return from_carried(item, owner=owner, observation=entry.observation if entry is not None else None)


# -- owned copies ------------------------------------------------------------------------------------------------


class NoCopies:
    """Owned copies that cannot be told (S8: a set or unique item is kept, keep.py K4): the replay's default."""

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        del facts
        return None


NO_COPIES = NoCopies()


class CalledCopies:
    """Owned copies from a callable (api.py `FieldHands.copies`)."""

    def __init__(self, copies: Callable[[ItemFacts], Sequence[ItemFacts] | None]) -> None:
        self.called = copies

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        return self.called(facts)


class TableCopies:
    """Owned copies from a table, keyed by unit id, else name, else code (tests); `default` for any other item."""

    def __init__(
        self, table: Mapping[int | str, Sequence[ItemFacts] | None], default: Sequence[ItemFacts] | None = None
    ) -> None:
        self.table, self.default = table, default

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        return next((self.table[key] for key in (facts.unit_id, facts.name, facts.code) if key in self.table),
                    self.default)  # fmt: skip


# -- the entry point ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Look:
    """What the ground site knows of a look besides the items' facts: `had` the carry-one classes held already
    (game/memory.py `had_already`: a second Wirt's Leg is left), `shown` the units the loot filter shows (Drop.source
    'shown': the size classes G14 / G15 take only those)."""

    had: frozenset[int] = frozenset()
    shown: frozenset[int] = frozenset()


NO_LOOK = Look()


@dataclass(frozen=True)
class Assessor:
    """The one way items are judged: `appraiser` the price source, `copies` the owned copies (keep.py K4-K6),
    `counted` the owned copies of a base for a row's `keep_up_to` on the ground (live: loot/value.py `owned_bases`;
    None: not counted, the cap does not hold)."""

    appraiser: Appraiser
    copies: OwnedCopies = NO_COPIES
    counted: OwnedCount | None = None

    def assess(self, facts: ItemFacts, site: Site, look: Look = NO_LOOK) -> Assessment:
        """`facts` judged at `site`; `look` what the ground site knows besides the facts."""
        return self.assess_all([facts], site, look)[0]

    def assess_all(self, items: Sequence[ItemFacts], site: Site, look: Look = NO_LOOK) -> list[Assessment]:
        """`items` judged at `site`, in their order. TOWN and GAMBLE judge them together (the town's order and the
        copies kept in the same visit, api.py `town_verdicts`); every other site one at a time, as it does today."""
        if site == Site.GROUND:
            found = [self._ground(facts, look) for facts in items]
        elif site == Site.FIELD:
            found = [self._field(facts) for facts in items]
        elif site == Site.SHOP:
            found = [self._shop(facts) for facts in items]
        elif site in AS_THE_LOOPS:
            found = [assessment for facts in items for assessment in self._town([facts], site)]
        else:
            found = self._town(items, site)
        return [_guarded(assessment) for assessment in found]

    # -- ground --

    def _ground(self, facts: ItemFacts, look: Look) -> Assessment:
        """The GOOD pickup level's judgement with the loop on (macros/pickmode.py `_taken`, phase 2A): a plain base by
        the allowlist (base_floor.py PLAIN_BY_RULES), else `judge`; a magic or rare drop that is no sure valuable is the
        field identify's or left (`_field_class`); whatever the marks point at is picked (D7)."""
        plain = base_floor.is_plain(facts.code, facts.quality) and not facts.marked and not facts.runeword
        junk = base_floor.facts_junk(facts) if plain and not base_floor.PLAIN_BY_RULES else None
        plain = plain and (base_floor.PLAIN_BY_RULES or junk is not None)  # switch off: only the floor's junk
        field, for_field = None, False
        if junk is not None:
            verdict = GroundVerdict(False, False, None, '', junk)
        elif plain:
            verdict = self._plain(facts)
        elif facts.runeword:  # D12 (2026-10-23): the game's flag; never left
            verdict = GroundVerdict(True, True, Then.KEEP, 'G1', f'a runeword ({facts.runeword})')
        elif (left := ethereal_only(facts)) is not None:
            verdict = GroundVerdict(False, False, None, '', left)
        else:
            verdict = ground_judge.judge(facts, owned=self.counted, had=look.had)
            if facts.marked and not verdict.pick and verdict.reason != HAD:
                # D7: pickmode.py `sure` takes every drop the marks point at, a row unread or capped too
                klass = 'G2' if facts.quality not in QUALITY_NAMES else 'G1'
                verdict = GroundVerdict(True, True, _then(facts), klass, 'the loot marks point at it')
            field = _field_class(facts, verdict, look)
            for_field = _fields(facts, verdict)
            if for_field and field is None:
                left = f'{verdict.klass} is no field class (api.py CLASSES)' if verdict.pick else verdict.reason
                verdict = GroundVerdict(False, False, None, '', left)
            elif for_field and field != verdict.klass:
                cells = facts.size[0] * facts.size[1]
                verdict = GroundVerdict(True, False, Then.IDENTIFY, field or '',
                                        f'a big {facts.quality_name} item ({cells} cells)')  # fmt: skip
        outcome = Outcome.PICK if verdict.pick else Outcome.LEAVE
        rule = verdict.klass or ('allowlist' if plain else 'left')
        return Assessment(facts, Site.GROUND, outcome, rule, verdict.said(), ground=verdict, field=field,
                          for_field=for_field and verdict.pick, plain=plain)  # fmt: skip

    def _plain(self, facts: ItemFacts) -> GroundVerdict:
        """A white or grey weapon or armor the marks do not point at: taken only by an allowlist entry its ground read
        matches (the player, 2026-10-23 ~00:50: "every base must worth 4+ist at least"; base_floor.py PLAIN_BY_RULES,
        the rule macros/pickmode.py `plain_base` applied, a must-have row's base a must-have as `_allowlisted` made
        it)."""
        if facts.rolls is None:
            return GroundVerdict(False, False, None, '', 'its rolls unread: on no allowlist entry ("unread bases '
                                 'filled the stash", 2026-10-17)')  # fmt: skip
        why = base_floor.allowed(facts)
        if why is None:
            return GroundVerdict(False, False, None, '', base_floor.facts_junk(facts) or PLAIN_LEFT)
        based = ground_judge.base_verdict(facts, owned=self.counted)
        rowed = based is not None and based.pick
        must = rowed and based is not None and based.must_have
        return GroundVerdict(True, must, Then.KEEP, based.klass if rowed and based is not None else 'allowlist', why)

    # -- field --

    def _field(self, facts: ItemFacts) -> Assessment:
        """api.py `Field._judge`: the decision on one identified item, then the field's own guard (`droppable`); an
        unidentified one waits for the Tome, a magic amulet for Cain (api.py `to_cain`)."""
        if not facts.identified and facts.quality >= MAGIC:
            if _cain(facts):
                why = 'a magic amulet: carried to Cain unidentified (api.py RINGS_TO_CAIN)'
                return Assessment(facts, Site.FIELD, Outcome.IDENTIFY, CAIN, why)
            return Assessment(facts, Site.FIELD, Outcome.IDENTIFY, 'K2', 'unidentified: the Tome first')
        value = self.appraiser.appraise(facts)
        read = facts.observation.get('item') if facts.observation is not None else None
        if value is None or not isinstance(read, Mapping) or read.get('identified') is not True:
            why = 'no identified read or appraisal: kept (S8), Cain and the town decide'
            return Assessment(facts, Site.FIELD, Outcome.KEEP, S8, why, value)
        [(_, _, decision)] = decide_all([(facts, value)], self.copies.copies)
        if decision.action != Action.DROP:
            return Assessment(facts, Site.FIELD, ACTIONS[decision.action], decision.rule, decision.reason, value,
                              decision)  # fmt: skip
        named = facts.quality in (SET, UNIQUE)
        refused = droppable(facts, value, self.copies.copies(facts) if named else None)
        if refused is not None:
            return Assessment(facts, Site.FIELD, Outcome.KEEP, GUARD, f'{decision.said()}; not dropped: {refused}',
                              value, decision, guard=refused)  # fmt: skip
        reason = f'a surplus copy, not better, cheap: {decision.reason}' if named else decision.reason
        return Assessment(facts, Site.FIELD, Outcome.DROP, decision.rule, f'in the field: {decision.rule} {reason}',
                          value, decision)  # fmt: skip

    # -- town, gamble, card, corpus --

    def _town(self, items: Sequence[ItemFacts], site: Site) -> list[Assessment]:
        """api.py `town_verdicts` over the identified items (`town_sold`: the unidentified wait for Cain)."""
        judged = [replace(facts, owner=Owner.LOOP) if site in AS_THE_LOOPS else facts for facts in items]
        priced = [(facts, self.appraiser.appraise(facts)) for facts in judged if facts.identified]
        verdicts = iter(town_verdicts(priced, self.copies.copies))
        found = []
        for facts in judged:
            if not facts.identified:
                why = 'unidentified: Cain identifies it, never given up unread'
                found.append(Assessment(facts, site, Outcome.IDENTIFY, 'K2', why))
                continue
            found.append(_from_town(next(verdicts), site))
        return found

    # -- shop --

    def _shop(self, facts: ItemFacts) -> Assessment:
        """shop/service.py `assess`: a target when the triage prices it (`shop_priced`) or a reviewed pattern
        (shop/rules.py `match_item`) names it."""
        value = self.appraiser.appraise(facts)
        reasons = [priced] if (priced := shop_priced(value)) is not None else []
        if facts.observation is not None:
            from inventory_tracking.shop.rules import match_item  # here: the shop's decode tables are heavy

            read = dict(facts.observation)
            # the shop's decode names the item type (shop/capture.py); an identify read does not: the facts' type
            read['item'] = {'item_type': facts.base_type, 'base_name': facts.base_name, **(read.get('item') or {})}
            reasons += match_item(read)
        if not reasons:
            why = 'no priced verdict and no reviewed pattern'
            return Assessment(facts, Site.SHOP, Outcome.PASS, 'shop', why, value)
        return Assessment(facts, Site.SHOP, Outcome.BUY, 'shop', '; '.join(reasons), value)


def _from_town(verdict: TownVerdict, site: Site) -> Assessment:
    decision, facts, value = verdict.decision, verdict.facts, verdict.value
    if decision is None:
        return Assessment(facts, site, Outcome.KEEP, S8, verdict.why, value)
    if verdict.sold:
        return Assessment(facts, site, Outcome.VENDOR, decision.rule, verdict.why, value, decision)
    if decision.gives_up:
        why = f'{decision.said()}; kept: {verdict.why}'
        return Assessment(facts, site, Outcome.KEEP, GUARD, why, value, decision, guard=verdict.why)
    return Assessment(facts, site, ACTIONS[decision.action], decision.rule, decision.reason, value, decision)


HAD = 'one is had already: the game takes no second'  # ground_judge.py `judge`'s carry-one leave
# Rare merc polearms are taken only when ethereal (the player, 2026-10-24: "refine it with actual traderie sales", then
# "implement both"): Traderie's Recent Trades of these bases hold 10 genuine rare sales, every one ethereal (6-15 Jah);
# no non-ethereal rare sold. The ethereal ones are the field identify's and the want rows rare-merc-polearm-eth-*
# keep those that match the sales (guides/warlock.html, the SHOW Rare Merc Polearms row)
ETHEREAL_ONLY_RARE = ('Thresher', 'Giant Thresher', 'Cryptic Axe', 'Great Poleaxe', 'Colossus Voulge', 'Mancatcher')


@cache
def ethereal_only_codes() -> frozenset[str]:
    """The ETHEREAL_ONLY_RARE bases' codes, from the game data."""
    from inventory_tracking.items.metadata import metadata

    return frozenset(row['code'] for row in metadata()['bases'].values() if row.get('name') in ETHEREAL_ONLY_RARE)


def ethereal_only(facts: ItemFacts) -> str | None:
    """Why the ground leaves a rare drop of an ETHEREAL_ONLY_RARE base: read as not ethereal and no mark on it;
    None to judge it as any other (an unread ethereal flag is judged too)."""
    if facts.quality != RARE or facts.ethereal is not False or facts.marked or facts.code not in ethereal_only_codes():
        return None
    return 'a non-ethereal rare merc polearm: no such rare sold (Traderie Recent Trades, 2026-10-24)'


def _then(facts: ItemFacts) -> Then:
    return Then.KEEP if facts.identified else Then.IDENTIFY


def _fields(facts: ItemFacts, verdict: GroundVerdict) -> bool:
    """Whether a pick of the unidentified magic or rare `facts` is only the field identify's: not a rune, gem, charm or
    jewel (G1), a rare ring or amulet (JEWELRY_SURE) or what the marks point at, which the ground takes whatever the
    field (pickmode.py `sure`)."""
    if facts.quality not in (MAGIC, RARE) or facts.identified or facts.marked or verdict.klass == 'G1':
        return False
    return not (facts.base_type in JEWELRY and facts.quality in JEWELRY_SURE)


def _field_class(facts: ItemFacts, verdict: GroundVerdict, look: Look) -> str | None:
    """The field identify's class for a magic or rare drop (api.py `Field.takes` but its loop and source gate, which
    stay the field's: R4): the ground verdict's identify class when api.py CLASSES has it, else G15 over the pickup's
    cell cap or G14 from BIG_CELLS cells for a drop the filter shows (`Look.shown`); None for none or with the field
    identify off."""
    if not loot_api.FIELD_IDENTIFY or facts.quality not in (MAGIC, RARE) or facts.identified or facts.marked:
        return None
    if verdict.pick and verdict.then == Then.IDENTIFY and verdict.klass in loot_api.CLASSES:
        return verdict.klass
    cells = facts.size[0] * facts.size[1]
    if facts.unit_id not in look.shown or cells < loot_api.BIG_CELLS:
        return None
    if cells > APPRAISAL.pickup_shown_cells:
        return 'G15' if loot_api.FIELD_OVERSIZE and 'G15' in loot_api.CLASSES else None
    return 'G14' if loot_api.FIELD_BIG and 'G14' in loot_api.CLASSES else None


def _cain(facts: ItemFacts) -> bool:
    """api.py `to_cain` on the facts: an unidentified magic amulet (and ring, FIELD_IDENTIFY_RINGS off) carried to
    Cain unidentified (RINGS_TO_CAIN)."""
    if not loot_api.RINGS_TO_CAIN or facts.identified or facts.quality != MAGIC:
        return False
    if loot_api.FIELD_IDENTIFY_RINGS and facts.base_type == 'ring':
        return False
    return facts.base_type in loot_api.NAMED_SMALL


def shop_priced(value: Value | None) -> str | None:
    """Why the triage alone makes a vendor's item a target (shop/service.py `priced`: sold, or slowly, at PRICED_IST
    or more by the lower quartile, else the median), None when it does not."""
    from inventory_tracking.shop.service import PRICED_IST  # here: the shop's capture code is heavy

    if value is None or value.verdict not in ('sell', 'slow') or value.band is None:
        return None
    price = value.band.q1 if value.band.q1 is not None else value.band.median
    if price is None or price < PRICED_IST:
        return None
    return f'priced: {value.verdict} at {price:.3g} Ist (asks)'


# -- the last guard ----------------------------------------------------------------------------------------------


def never_trash(assessment: Assessment) -> str | None:
    """Why `assessment` must not give its item up, None when it may (or keeps it). The rulings: S1 the player's items,
    S2 runes, gems, potions, set/unique charms, S8 unidentified; "we absolutely MUST NOT trash good items" (2026-10-23):
    an always-kept want row, DUPLICATE_IST by its own rolls. A low Gheed's Fortune is sold in town (keep.py
    GHEEDS_BY_ROLL, the player 2026-10-21: "low rolls doesn't sell"). Pure."""
    if assessment.outcome not in GIVE_UP:
        return None
    facts, site = assessment.facts, assessment.site
    kind = facts.base_type
    if facts.runeword:
        return f'a runeword ({facts.runeword})'  # D12 (2026-10-23): never left, put down or sold
    if site == Site.GROUND:
        if kind in ALWAYS_PICKED:
            return 'a rune, gem, charm or jewel: always picked'
        if facts.quality in (SET, UNIQUE):
            return 'a set or unique item: always picked, then judged'
        group = ground_judge.material(facts.code)
        if group is not None and group not in CARRY_ONE:
            return f'a material ({group}): always picked'
        return None
    if facts.owner != Owner.LOOP:
        return f"not the loop's (owner {facts.owner.value})"
    if not facts.identified and facts.quality >= MAGIC:
        return 'unidentified'
    if kind in NEVER_GIVEN_UP or facts.code in NEVER_SOLD_CODES:
        return "never given up (runes, gems, potions, the Sunder, organs, tools, Wirt's Leg)"
    low_gheeds = site in TOWN_SITES and assessment.outcome == Outcome.VENDOR and gheeds_low(facts) is not None
    if kind in CHARMS and facts.quality in (SET, UNIQUE) and not low_gheeds:
        return 'a set or unique charm'
    if site == Site.FIELD and kind in CHARMS | JEWELS:
        return 'a charm or jewel: never put down in the field'
    value = assessment.value
    if value is not None and (kept := [want for want in value.wants if want.always_keep]):
        return f'always kept: {kept[0].label}'
    if value is not None and value.worth_ist is not None and value.worth_ist >= DUPLICATE_IST and not low_gheeds:
        return f'worth {value.worth_ist:.3g} Ist by its rolls'
    return None


def _guarded(assessment: Assessment) -> Assessment:
    refused = never_trash(assessment)
    if refused is None:
        return assessment
    LOG.warning('Loot: assess: never given up: %s (%s)', assessment.said(), refused)
    kept = Outcome.PICK if assessment.site == Site.GROUND else Outcome.KEEP
    why = f'never given up: {refused} (the rules said {assessment.outcome.value} {assessment.rule}: {assessment.why})'
    return replace(assessment, outcome=kept, rule=NEVER_TRASH, why=why, guard=refused)


# -- the shadow ---------------------------------------------------------------------------------------------------

# The old decision beside the entry point's while a site moves (design.md §10.4, phase 2A): one line where they
# differ, once per key ("Macro: loot: assess: ground: magic Monarch: new pick G6 / old leave (new decides)")
SHADOW = True
SHADOW_SAID: set[tuple[Any, ...]] = set()
SHADOW_MOST = 4096
SHADOW_PREFIX = 'Macro: loot: assess:'


def shadow(key: tuple[Any, ...], site: Site, title: str, new: str, old: str, *, new_decides: bool) -> str | None:
    """Log the old decision beside the new one when they differ, once per `key`; the line logged, else None."""
    if not SHADOW or new == old or key in SHADOW_SAID:
        return None
    if len(SHADOW_SAID) > SHADOW_MOST:
        SHADOW_SAID.clear()
    SHADOW_SAID.add(key)
    line = f'{SHADOW_PREFIX} {site.value}: {title}: new {new} / old {old} ({"new" if new_decides else "old"} decides)'
    LOG.info('%s', line)
    return line


def live() -> Assessor:
    """The live assessor: the identify worker's appraisals (BOOK), the collection's owned copies (read-only), the
    owned bases' count for the ground's caps."""
    from inventory_tracking.loot.value import CollectionCopies, owned_bases

    return Assessor(BookAppraiser(), CollectionCopies(), owned_bases)
