"""The one assessment entry point (inventory_tracking/loot/assess.py; loot/design.md §10; the player, 2026-10-23:
"we need to have one dedicated place where all assessments are happening - reuse it everywhere - single entry point -
easy to test"): facts in, an assessment per site out, with a table of prices and no knowledge base loaded.

- The site table: the must-keep items (runes, gems, set/unique charms, the player's items, an expensive duplicate, a
  wanted rare amulet, a 4os eth merc base, a Monarch of Deflecting) and the junk, at every site that sees them.
- The acceptance table (fixtures/valuables.json) through the entry point: the same decisions as test_valuables.py's
  new layers on every aspect; on the ground the plain bases follow the 2026-10-23 allowlist, which the table's older
  rows predate (ALLOWLIST_OVER_THE_TABLE, each named).
- The live ground pickup (macros/pickmode.py, GOOD level, the loop on) gives the same pick or leave on every fixture
  item as today's look reads it: the check phase 2 needs before the pickup moves onto the entry point.
- The last guard (`never_trash`) refuses every give-up of a never-given-up item, and never fires on the composed rules.
"""

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.game.records import VALUABLE, Carried, Drop, Loot, Rolls
from inventory_tracking.identify.service import verdict_for
from inventory_tracking.loot import api, assess as assess_module, base_floor, ground_judge, today, value as loot_value
from inventory_tracking.loot.api import TownVerdict, droppable, town_verdicts
from inventory_tracking.loot.assess import (
    NEVER_TRASH,
    NO_PRICES,
    S8,
    Assessment,
    Assessor,
    BookAppraiser,
    FakeAppraiser,
    Look,
    Outcome,
    Price,
    ResultAppraiser,
    Site,
    TableCopies,
    carried_facts,
    live,
    never_trash,
    shop_priced,
    triage_verdict,
)
from inventory_tracking.loot.facts import BY_FLAG, ItemFacts, Owner, Where, base_of_code, from_carried, from_drop
from inventory_tracking.loot.keep import Action, Decision, decide
from inventory_tracking.loot.shadow import Appraised, Book
from inventory_tracking.loot.value import CollectionCopies, Value, appraise_result
from inventory_tracking.macros import pickmode
from inventory_tracking.shop.service import priced
from tests.inventory_tracking.loot.test_valuables import (
    CASES,
    counted,
    facts_of,
    ground_facts,
    observation,
    owned_of,
    value_of,
)


BY_ID = {case['id']: case for case in CASES}
REPLAYED = json.loads((Path(__file__).parent / 'fixtures' / 'assess_replay.json').read_text())['reads']


def case_item(case_id: str) -> dict[str, Any]:
    return BY_ID[case_id]['item']


def assessor_for(case: Mapping[str, Any], facts: ItemFacts) -> Assessor:
    """The entry point with the case's price (a table row) and owned copies: no knowledge base, no collection."""
    return Assessor(FakeAppraiser({facts.unit_id: value_of(dict(case), facts)}), TableCopies({}, owned_of(dict(case))),
                    counted(dict(case)))  # fmt: skip


# -- the site table ----------------------------------------------------------------------------------------------

# A wanted rare amulet: +2 Warlock skills, 10 FCR, 50 life, 20 to every resistance (the bar's Warlock amulet row,
# loot/data/wants.json bar-warlock-amulet-three-good: always kept); its code from the acceptance table's amulets
WARLOCK_AMULET = {
    'base': 'Amulet', 'code': case_item('rare_amulet_fcr_kept')['code'], 'quality': 'rare', 'name': 'Rune Gorget',
    'rolls': {'83:7': 2, '105:0': 10, '7:0': 50 << 8, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20},
}  # fmt: skip
# A low Gheed's Fortune (keep.py GHEEDS_BY_ROLL: magic find 30, gold find 100: sold in town, never put down)
LOW_GHEEDS = {**case_item('gheeds_fortune_duplicate'), 'rolls': {'80:0': 30, '79:0': 100}}


def row(case_id: str, site: Site, outcome: Outcome, rule: str | None = None, **given: Any):
    """A site-table row from an acceptance case: its item, price and owned copies, `given` overriding them."""
    case = {**BY_ID[case_id], **given}
    return pytest.param(case, site, outcome, rule, id=f'{case_id}-{site.value}')


def made(case_id: str, item: dict[str, Any], site: Site, outcome: Outcome, rule: str | None = None, **given: Any):
    case = {'id': case_id, 'item': item, 'owned': None, 'value': {'worth': None, 'verdict': None}, **given}
    return pytest.param(case, site, outcome, rule, id=f'{case_id}-{site.value}')


VENDOR = {'worth': 0.1, 'verdict': 'vendor'}

SITE_TABLE = [
    # Must keep: runes, gems, set/unique charms (S2), whatever their price
    row('cheap_rune_kept', Site.GROUND, Outcome.PICK, 'G1'),
    row('cheap_rune_kept', Site.TOWN, Outcome.KEEP, 'K1'),
    row('cheap_rune_kept', Site.FIELD, Outcome.KEEP, 'K1'),
    row('cheap_rune_kept', Site.GAMBLE, Outcome.KEEP, 'K1'),
    row('cheap_gem_kept', Site.GROUND, Outcome.PICK, 'G1'),
    row('cheap_gem_kept', Site.TOWN, Outcome.KEEP, 'K1'),
    row('annihilus_duplicate', Site.GROUND, Outcome.PICK, 'G1'),
    row('annihilus_duplicate', Site.TOWN, Outcome.KEEP, 'K1'),
    row('annihilus_duplicate', Site.FIELD, Outcome.KEEP, 'K1'),
    row('torch_duplicate', Site.TOWN, Outcome.KEEP, 'K1'),
    row('sunder_duplicate', Site.TOWN, Outcome.KEEP, 'K1'),
    # The low Gheed's Fortune: sold in town (the player, 2026-10-21: "low rolls doesn't sell"), never put down
    made('low_gheeds', LOW_GHEEDS, Site.TOWN, Outcome.VENDOR, 'K1', value=VENDOR),
    made('low_gheeds', LOW_GHEEDS, Site.FIELD, Outcome.KEEP, 'guard', value=VENDOR),
    # The player's items (S1): never touched; the card judges an item as the loop's (what the loop would do)
    row('players_item_on_protected_cell', Site.TOWN, Outcome.NEVER_TOUCH, 'K0'),
    row('players_item_on_protected_cell', Site.FIELD, Outcome.NEVER_TOUCH, 'K0'),
    row('players_item_on_protected_cell', Site.GAMBLE, Outcome.NEVER_TOUCH, 'K0'),
    row('players_item_by_print_in_cube', Site.TOWN, Outcome.NEVER_TOUCH, 'K0'),
    row('owner_unknown_is_the_players', Site.TOWN, Outcome.NEVER_TOUCH, 'K0'),
    row('players_item_on_protected_cell', Site.CARD, Outcome.VENDOR, 'K8'),
    # An expensive duplicate (N1): kept though worse than the owned copy
    row('expensive_duplicate_worse_is_kept', Site.TOWN, Outcome.KEEP, 'K5'),
    row('expensive_duplicate_worse_is_kept', Site.FIELD, Outcome.KEEP, 'K5'),
    row('expensive_duplicate_worse_is_kept', Site.CARD, Outcome.KEEP, 'K5'),
    # A wanted rare amulet, appraised vendor: an always-kept want row (K3)
    made('wanted_rare_amulet', WARLOCK_AMULET, Site.TOWN, Outcome.KEEP, 'K3', value=VENDOR),
    made('wanted_rare_amulet', WARLOCK_AMULET, Site.FIELD, Outcome.KEEP, 'K3', value=VENDOR),
    made('wanted_rare_amulet', WARLOCK_AMULET, Site.GAMBLE, Outcome.KEEP, 'K3', value=VENDOR),
    # A 4os eth merc base (the Insight Giant Thresher): picked as a must-have, always kept
    row('merc_gt_eth_4os', Site.GROUND, Outcome.PICK, 'G3'),
    row('merc_gt_eth_4os', Site.TOWN, Outcome.KEEP, 'K3'),
    row('merc_gt_eth_4os', Site.TOWN, Outcome.KEEP, 'K3', value=VENDOR),
    # The 4os Monarch of Deflecting ("we absolutely want to keep it", 2026-10-20): picked to identify, then kept
    row('monarch_of_deflecting_4os', Site.GROUND, Outcome.PICK, 'G6'),
    row('monarch_of_deflecting_4os', Site.FIELD, Outcome.KEEP, 'K3'),
    row('monarch_of_deflecting_4os', Site.TOWN, Outcome.KEEP, 'K3', value=VENDOR),
    # Unidentified: never given up unread (S8)
    row('unidentified_never_dropped', Site.FIELD, Outcome.IDENTIFY, 'K2'),
    row('unidentified_never_dropped', Site.TOWN, Outcome.IDENTIFY, 'K2'),
    row('tome_of_identify_never_moved', Site.TOWN, Outcome.NEVER_TOUCH, 'K1'),
    row('wirts_leg_picked_and_never_sold', Site.TOWN, Outcome.KEEP, 'K1'),
    # Junk is junk: a cheap worse copy sold, the field puts down what fails there
    row('goblin_toe_third_copy_worse_is_dropped', Site.TOWN, Outcome.VENDOR, 'K6'),
    row('goblin_toe_third_copy_worse_is_dropped', Site.FIELD, Outcome.KEEP, 'guard'),  # a small unique: Cain's
    row('bloodtree_stump_surplus_not_better_cheap_dropped_in_field', Site.FIELD, Outcome.DROP, 'K8'),
    row('vendor_band_item_dropped', Site.TOWN, Outcome.VENDOR, 'K8'),
    row('vendor_band_item_dropped', Site.FIELD, Outcome.DROP, 'K8'),
    row('gloves_bowyers_of_alacrity_dropped_in_field', Site.FIELD, Outcome.DROP, 'K8'),
    row('boots_rare_october_6_war_boots_vendor_dropped', Site.TOWN, Outcome.VENDOR, 'K8'),
    row('boots_rare_october_6_war_boots_vendor_dropped', Site.GAMBLE, Outcome.VENDOR, 'K8'),
    row('dagger_3os_without_paid_staffmod_left', Site.GROUND, Outcome.LEAVE, 'allowlist'),
    row('white_plain_0os_monarch_left', Site.GROUND, Outcome.LEAVE, 'allowlist'),
    row('rare_non_elite_armor_left', Site.GROUND, Outcome.LEAVE, 'left'),
    # No appraisal: kept (S8)
    row('vendor_band_item_dropped', Site.TOWN, Outcome.KEEP, S8, value=None),
    row('vendor_band_item_dropped', Site.FIELD, Outcome.KEEP, S8, value=None),
]


def site_facts(case: Mapping[str, Any], site: Site) -> ItemFacts:
    return ground_facts(dict(case)) if site == Site.GROUND else facts_of(case['item'])


def priced_as(case: Mapping[str, Any], facts: ItemFacts) -> Value | None:
    return None if 'value' in case and case['value'] is None else value_of(dict(case), facts)


@pytest.mark.parametrize(('case', 'site', 'outcome', 'rule'), SITE_TABLE)
def test_the_site_table(case, site, outcome, rule):
    facts = site_facts(case, site)
    found = Assessor(FakeAppraiser({facts.unit_id: priced_as(case, facts)}), TableCopies({}, owned_of(case)),
                     counted(case)).assess(facts, site)  # fmt: skip
    assert found.outcome == outcome, found.said()
    if rule is not None:
        assert found.rule == rule, found.said()
    assert found.why, found.said()
    assert found.rule != NEVER_TRASH, found.said()


def test_the_must_have_merc_base_is_a_must_have_on_the_ground():
    case = BY_ID['merc_gt_eth_4os']
    facts = ground_facts(case)
    found = assessor_for(case, facts).assess(facts, Site.GROUND)
    assert found.ground is not None
    assert found.ground.must_have, found.said()
    assert 'allowlisted' in found.ground.reason, found.said()


def test_town_judges_copies_carried_together_best_first():
    """Two Goblin Toes carried in one visit (56 % and 50 % ED, 53 % owned): the 56 % kept (better than the owned),
    then counted as owned for the 50 %, which is sold (api.py `town_verdicts`)."""
    spec = {**case_item('goblin_toe_third_copy_worse_is_dropped'), 'ranges': {'16:0': [50, 60]}}
    worse, best = facts_of({**spec, 'rolls': {'16:0': 50}}, 1), facts_of({**spec, 'rolls': {'16:0': 56}}, 2)
    owned = [facts_of({**spec, 'rolls': {'16:0': 53}}, 3, owner=Owner.PLAYER)]
    assessor = Assessor(FakeAppraiser({1: Price(0.65, 'slow'), 2: Price(0.85, 'slow')}), TableCopies({}, owned))
    found = {a.facts.unit_id: a for a in assessor.assess_all([worse, best], Site.TOWN)}
    assert found[2].outcome == Outcome.KEEP, found[2].said()
    assert found[1].outcome == Outcome.VENDOR, found[1].said()
    assert '53, 56' in found[1].why


def test_the_card_judges_each_item_alone_as_the_loops():
    spec = {**case_item('goblin_toe_third_copy_worse_is_dropped'), 'ranges': {'16:0': [50, 60]}}
    owned = [facts_of({**spec, 'rolls': {'16:0': 53}}, 3, owner=Owner.PLAYER)]
    mine = [facts_of({**spec, 'rolls': {'16:0': 56}}, 2, owner=Owner.PLAYER),
            facts_of({**spec, 'rolls': {'16:0': 50}}, 1, owner=Owner.PLAYER)]  # fmt: skip
    assessor = Assessor(FakeAppraiser({}, Price(0.65, 'slow')), TableCopies({}, owned))
    found = assessor.assess_all(mine, Site.CARD)
    assert [a.outcome for a in found] == [Outcome.KEEP, Outcome.VENDOR], [a.said() for a in found]
    assert all(a.facts.owner == Owner.LOOP for a in found)


def test_a_drop_whose_filter_shows_it_is_a_big_field_item():
    """G14 / G15 by size: only a drop the loot filter shows (`Look.shown`), as api.py `Field.takes`."""
    spec = case_item('boots_magic_left_on_the_ground')
    facts = replace(ground_facts({'item': spec}), size=(2, 2))
    assessor = Assessor(FakeAppraiser({}))
    assert assessor.assess(facts, Site.GROUND).outcome == Outcome.LEAVE
    found = assessor.assess(facts, Site.GROUND, Look(shown=frozenset({facts.unit_id})))
    assert (found.outcome, found.rule) == (Outcome.PICK, 'G14'), found.said()
    big = assessor.assess(replace(facts, size=(2, 4)), Site.GROUND, Look(shown=frozenset({facts.unit_id})))
    assert big.rule == 'G15', big.said()


def test_a_second_wirts_leg_is_left_while_one_is_had():
    facts = ground_facts(BY_ID['wirts_leg_picked_and_never_sold'])
    assessor = Assessor(FakeAppraiser({}))
    assert assessor.assess(facts, Site.GROUND).outcome == Outcome.PICK
    assert facts.txt is not None
    assert assessor.assess(facts, Site.GROUND, Look(had=frozenset({facts.txt}))).outcome == Outcome.LEAVE


# -- the shop ----------------------------------------------------------------------------------------------------


def triage_result(verdict: str, q1: float | None, median: float | None) -> dict[str, Any]:
    band = {key: value for key, value in (('q1_ist', q1), ('median_ist', median)) if value is not None}
    return {'triage': {'verdict': verdict, 'band': band}}


SHOP_TRIAGES = [
    ('sell', 3.0, 5.0),
    ('slow', None, 3.0),  # no lower quartile: the median
    ('sell', 2.0, 9.0),  # the lower quartile under PRICED_IST
    ('vendor', 9.0, 9.0),
    ('check', 9.0, 9.0),
    ('slow', 2.6, 2.6),
]


@pytest.mark.parametrize(('verdict', 'q1', 'median'), SHOP_TRIAGES)
def test_the_shops_priced_rule_is_shop_services(verdict, q1, median):
    result = triage_result(verdict, q1, median)
    facts = facts_of(case_item('vendor_band_item_dropped'))
    value = appraise_result(facts, result)
    assert (shop_priced(value) is not None) == priced(result['triage'])
    found = Assessor(FakeAppraiser({facts.unit_id: value})).assess(facts, Site.SHOP)
    assert found.outcome == (Outcome.BUY if priced(result['triage']) else Outcome.PASS), found.said()


def test_a_shop_item_a_reviewed_pattern_names_is_a_target():
    """shop/rules.py `match_item`: a Jeweler's Monarch of Deflecting 4os, with no price at all (the shop's read
    holds the sockets as stat 194, items/stat_constants.py SOCKETS)."""
    spec = case_item('monarch_of_deflecting_4os')
    facts = facts_of({**spec, 'rolls': {**spec['rolls'], '194:0': 4}})
    found = Assessor(FakeAppraiser({})).assess(facts, Site.SHOP)
    assert found.outcome == Outcome.BUY, found.said()
    assert 'Deflecting' in found.why


# -- the acceptance table through the entry point ---------------------------------------------------------------

# The plain bases the 2026-10-23 allowlist decides otherwise than the acceptance table's older ground rows (the
# player, 2026-10-23 ~00:50: "every base must worth 4+ist at least"; rca/2026-10-23/base-pickups.md: the rows dropped
# under 4 Ist or unproven, the entries added). The entry point follows the allowlist, as the live pickup does
# (macros/pickmode.py PLAIN_BY_RULES); the table rows are phase 2's to update (loot/design.md §10)
ALLOWLIST_OVER_THE_TABLE = {
    'merc_colossus_voulge_eth_4os_superior': 'left: Colossus Voulge n1',
    'merc_dusk_eth_4os': 'left: merc-fortitude-dusk-eth-4os median 0.789',
    'warlock_dagger_3os_plus3_apocalypse': 'left: +3 Apocalypse alone fills 1.0, 0.79 (base-candidates.md §3)',
    'warlock_dagger_0os_elite_plus3_apocalypse': 'left: void-dagger-0os-plus3-apocalypse unproven',
    'merc_polearm_non_eth_left': 'picked: the KB key normal Giant Thresher 4os (median 4+)',
    'own_exile_sacred_rondache_4os_44res': 'left: non-eth 40-44 Rondache 0.5-3.59',
    'own_cure_corona_eth_3os': 'left: cure-helm-eth-superior-15ed only (Bone Visage / Demonhead)',
    'spirit_monarch_plain_4os_under_the_cap_kept': 'left: spirit-monarch-plain-4os median 0.789',
    'merc_matriarchal_spear_eth_4os_superior': 'left: Matriarchal Spear no band',
    'market_colossus_blade_superior_10ed_5os_left': 'picked: the KB key superior Colossus Blade 5os',
    'grimoire_white_0os_plus3_sigil_death': 'left: grimoire-2os-plus3-paid takes 2os only',
    'claw_runic_talons_superior_0os_plus3_phoenix_strike': 'left: the Phoenix Strike fills are 3os',
    'claw_greater_talons_3os_plus3_fade_left': 'picked: claw-3os-plus3-assassin-skills (Fade 8.6)',
    'claw_own_trap_death_sentry_first_copy_kept': 'left: own-claw-white-plus3-traps not allowlisted',
    'scepter_war_plus3_fist_of_the_heavens': 'left: scepter-plus3-foh-and-paladin-2 needs the second mod',
    'market_dusk_shroud_superior_15ed_0os': 'left: market-dusk-wire-superior-15ed-0os median 3.32',
    'targe_superior_45_res': 'left: a superior Targe is not a Sacred Targe row',
    'market_crystal_sword_superior_15ed_5os': 'left: crystal-sword-superior-15ed-4os only',
    'market_bone_shield_superior_15ed_0os': 'left: no allowlist entry',
}


# The table's identify rows of no field class (api.py CLASSES): the entry point picks a magic or rare item that is no
# sure valuable only for the field identify, as the live GOOD level (2026-10-23, phase 2A); the real item is taken by
# its size class instead (the table's item is 1x1)
FIELD_OVER_THE_TABLE = {
    'jewelers_archon_of_the_whale': 'G12 is no field class: a real Archon Plate (2x3) the filter shows is G14',
}


def aspect(name: str) -> list:
    return [pytest.param(case, id=case['id']) for case in CASES if name in case['expect']]


@pytest.mark.parametrize('case', aspect('decision'))
def test_the_decision_on_each_valuable_is_keep_decides(case):
    """test_valuables.py `test_the_new_keep_decision_on_each_valuable`, through the town site."""
    facts = facts_of(case['item'])
    found = assessor_for(case, facts).assess(facts, Site.TOWN)
    expect = case['expect']
    if expect['decision'] == 'identify':
        assert (found.outcome, found.rule) == (Outcome.IDENTIFY, expect['rule']), found.said()
        return
    direct = decide(facts, value_of(case, facts), owned_of(case))
    assert found.decision == direct, found.said()
    assert direct.action.value == expect['decision'], found.said()
    if 'rule' in expect:
        assert direct.rule == expect['rule'], found.said()


@pytest.mark.parametrize('case', aspect('town'))
def test_the_town_outcome_on_each_valuable_is_town_verdicts(case):
    facts = facts_of(case['item'])
    found = assessor_for(case, facts).assess(facts, Site.TOWN)
    [verdict] = town_verdicts([(facts, value_of(case, facts))], lambda _facts: owned_of(case))
    assert (found.outcome == Outcome.VENDOR) == verdict.sold, found.said()
    assert (found.outcome == Outcome.VENDOR) == (case['expect']['town'] == 'sell'), found.said()


@pytest.mark.parametrize('case', aspect('field'))
def test_the_field_outcome_on_each_valuable_is_the_field_routines(case):
    facts = facts_of(case['item'])
    value, owned = value_of(case, facts), owned_of(case)
    decision = decide(facts, value, owned)
    refused = droppable(facts, value, owned) if decision.action == Action.DROP else 'kept by the decision'
    found = assessor_for(case, facts).assess(facts, Site.FIELD)
    assert (found.outcome == Outcome.DROP) == (refused is None), found.said()
    assert found.outcome == (Outcome.DROP if case['expect']['field'] == 'drop' else Outcome.KEEP), found.said()


@pytest.mark.parametrize('case', aspect('ground'))
def test_the_ground_outcome_on_each_valuable(case):
    facts = ground_facts(case)
    found = assessor_for(case, facts).assess(facts, Site.GROUND)
    expected = case['expect']['ground'] == 'pick'
    plain = base_floor.is_plain(facts.code, facts.quality) and not facts.marked
    if plain:
        # the allowlist, or an own-use row under its cap (base_floor.OWN_USE: one eth 4os Archon, 2026-10-25)
        taken = base_floor.allowed(facts) or base_floor.own_use(facts, counted(case))
        assert (found.outcome == Outcome.PICK) == (taken is not None), found.said()
    elif case['id'] in FIELD_OVER_THE_TABLE:
        assert found.outcome == Outcome.LEAVE, found.said()
        real = replace(facts, size=(2, 3))  # the real base's size, the filter showing it: the size class G14
        bigger = assessor_for(case, real).assess(real, Site.GROUND, Look(shown=frozenset({real.unit_id})))
        assert (bigger.outcome, bigger.rule, bigger.field) == (Outcome.PICK, 'G14', 'G14'), bigger.said()
        return
    else:
        assert found.ground == ground_judge.judge(facts, owned=counted(case)), found.said()
    if case['id'] in ALLOWLIST_OVER_THE_TABLE:
        assert (found.outcome == Outcome.PICK) != expected, f'{found.said()}: the table and the allowlist agree now'
        return
    assert (found.outcome == Outcome.PICK) == expected, f'{found.said()} ({case["source"]})'
    if expected and 'then' in case['expect']:
        assert found.ground is not None, found.said()
        assert found.ground.then is not None, found.said()
        assert found.ground.then.value == case['expect']['then'], found.said()
    if expected and 'must_have' in case['expect']:
        assert found.ground is not None, found.said()
        assert found.ground.must_have == case['expect']['must_have'], found.said()


def test_the_allowlist_list_names_only_ground_cases():
    assert set(ALLOWLIST_OVER_THE_TABLE) <= {case['id'] for case in CASES if 'ground' in case['expect']}
    assert set(FIELD_OVER_THE_TABLE) <= {case['id'] for case in CASES if 'ground' in case['expect']}


# -- the live ground pickup gives the same answer ----------------------------------------------------------------

# Fixture items the live pickup judges otherwise, each a rule outside the loot layers or a site switch: none since
# phase 2A (2026-10-23: a magic or rare pick is the field's, as the live GOOD level; FIELD_OVER_THE_TABLE)
LIVE_OTHERWISE: dict[str, str] = {}


@pytest.mark.parametrize('case', [pytest.param(case, id=case['id']) for case in CASES])
def test_the_live_good_pickup_with_the_loop_on_agrees(case, monkeypatch):
    """macros/pickmode.py `_taken` (GOOD, the loop on, a fresh field memory) on the drop as today's look reads it
    (loot/today.py `drop`), against the entry point on the same read."""
    assert base_floor.PLAIN_BY_RULES  # the entry point's plain-base rule is this switch on
    field = api.Field(log=lambda *args: None)
    field.looping = lambda: True
    monkeypatch.setattr(pickmode, 'FIELD', field)
    monkeypatch.setattr(loot_value, 'owned_bases', counted(case))  # never the host's collection
    drop = today.drop(ground_facts(case))
    taken = pickmode._taken(drop, pickmode.SURE, Loot(drops=(drop,), game=('game', 1)), None)
    shown = frozenset({drop.unit_id}) if drop.source == 'shown' else frozenset()
    found = Assessor(FakeAppraiser({}), counted=counted(case)).assess(from_drop(drop), Site.GROUND, Look(shown=shown))
    if case['id'] in LIVE_OTHERWISE:
        assert (taken is not None) != (found.outcome == Outcome.PICK), found.said()
        return
    assert (taken is not None) == (found.outcome == Outcome.PICK), found.said()
    if taken is not None and found.ground is not None:
        assert taken.prized == (found.ground.must_have or drop.prized), found.said()


# -- the last guard ----------------------------------------------------------------------------------------------


def given_up(item: dict[str, Any], site: Site, outcome: Outcome, *, owner: Owner = Owner.LOOP, value=None, **facts):
    found = replace(facts_of(item, owner=owner), **facts)
    return Assessment(found, site, outcome, 'K8', 'a test', value)


RUNE = case_item('cheap_rune_kept')
ANNI = case_item('annihilus_duplicate')
JUNK = case_item('vendor_band_item_dropped')
REFUSED = [
    pytest.param(given_up(RUNE, Site.TOWN, Outcome.VENDOR), id='a-rune-sold'),
    pytest.param(given_up(RUNE, Site.GROUND, Outcome.LEAVE), id='a-rune-left'),
    pytest.param(given_up(case_item('cheap_gem_kept'), Site.FIELD, Outcome.DROP), id='a-gem-put-down'),
    pytest.param(given_up(ANNI, Site.TOWN, Outcome.VENDOR), id='a-unique-charm-sold'),
    pytest.param(given_up(ANNI, Site.GROUND, Outcome.LEAVE), id='a-unique-charm-left'),
    pytest.param(given_up(LOW_GHEEDS, Site.FIELD, Outcome.DROP), id='a-low-gheeds-put-down'),
    pytest.param(given_up(JUNK, Site.TOWN, Outcome.VENDOR, owner=Owner.PLAYER), id='the-players-sold'),
    pytest.param(given_up(JUNK, Site.FIELD, Outcome.DROP, owner=Owner.UNKNOWN), id='an-unknown-owners-put-down'),
    pytest.param(given_up(JUNK, Site.TOWN, Outcome.VENDOR, identified=False), id='an-unidentified-sold'),
    pytest.param(given_up(case_item('tome_of_identify_never_moved'), Site.TOWN, Outcome.VENDOR), id='a-tome-sold'),
    pytest.param(given_up(case_item('wirts_leg_picked_and_never_sold'), Site.TOWN, Outcome.VENDOR), id='wirts-sold'),
    pytest.param(given_up(case_item('gc_eldritch_skiller_life'), Site.FIELD, Outcome.DROP), id='a-charm-put-down'),
    pytest.param(given_up(case_item('merc_andariels_visage_first'), Site.GROUND, Outcome.LEAVE), id='a-unique-left'),
]


@pytest.mark.parametrize('assessment', REFUSED)
def test_the_guard_refuses_what_is_never_given_up(assessment):
    assert never_trash(assessment) is not None, assessment.said()


def test_the_guard_refuses_a_dear_or_always_kept_item():
    facts = facts_of(JUNK)
    dear = Assessment(facts, Site.TOWN, Outcome.VENDOR, 'K8', 'a test', loot_value.assess(facts, worth=1.2))
    assert never_trash(dear) == 'worth 1.2 Ist by its rolls'
    amulet = facts_of(WARLOCK_AMULET)
    wanted = Assessment(amulet, Site.FIELD, Outcome.DROP, 'K8', 'a test', loot_value.assess(amulet, worth=0.1))
    assert (never_trash(wanted) or '').startswith('always kept')


def test_the_guard_lets_junk_and_the_low_gheeds_sale_go():
    facts = facts_of(JUNK)
    assert (
        never_trash(Assessment(facts, Site.TOWN, Outcome.VENDOR, 'K8', '', loot_value.assess(facts, worth=0.1))) is None
    )
    assert never_trash(given_up(LOW_GHEEDS, Site.TOWN, Outcome.VENDOR)) is None
    assert never_trash(given_up(case_item('white_plain_0os_monarch_left'), Site.GROUND, Outcome.LEAVE)) is None
    assert never_trash(given_up(RUNE, Site.TOWN, Outcome.KEEP)) is None


def test_a_give_up_the_guard_refuses_is_kept(monkeypatch):
    """Were a rule to sell a rune, the entry point keeps it and says which rule tried."""
    facts = facts_of(RUNE)

    def selling(items, copies):
        del copies
        return [TownVerdict(f, v, Decision(Action.DROP, 'K8', 'worthless'), True, 'worthless') for f, v in items]

    monkeypatch.setattr(assess_module, 'town_verdicts', selling)
    found = Assessor(FakeAppraiser({}, Price(0.05, 'vendor'))).assess(facts, Site.TOWN)
    assert (found.outcome, found.rule) == (Outcome.KEEP, NEVER_TRASH), found.said()
    assert 'vendor K8' in found.why


@pytest.mark.parametrize('worth', [None, 0.05, 0.6, 1.0, 3.0])
@pytest.mark.parametrize('verdict', [None, 'vendor', 'slow', 'sell', 'check', 'self'])
def test_the_composed_rules_never_need_the_guard(worth, verdict):
    """Every acceptance item at every site, at any price and verdict: the guard never fires, so the rules alone keep
    what must be kept; and nothing worth DUPLICATE_IST is given up anywhere but on the ground."""
    for case in CASES:
        for site in Site:
            facts = site_facts(case, site)
            assessor = Assessor(
                FakeAppraiser({}, Price(worth, verdict)), TableCopies({}, owned_of(case)), counted(case)
            )
            found = assessor.assess(facts, site)
            assert found.rule != NEVER_TRASH, f'{case["id"]}: {found.said()}'
            if worth is not None and worth >= 1.0 and site != Site.GROUND and found.gives_up:
                assert gheeds_like(found.facts), f'{case["id"]}: {found.said()}'


def gheeds_like(facts: ItemFacts) -> bool:
    return facts.name == "Gheed's Fortune"


# -- the price sources -------------------------------------------------------------------------------------------

KB_RESULT = {'triage': {'verdict': 'slow', 'band': {'q1_ist': 0.6, 'median_ist': 0.9, 'sellers': 4}}}


def carried(unit: int, txt: int, quality: int, *, identified: bool = True) -> Carried:
    return Carried(unit, txt, 0, 0, (2, 2), quality, identified)


def test_the_book_appraiser_reads_the_identify_workers_appraisal():
    book = Book()
    spec = case_item('goblin_toe_first_copy_is_kept')
    read = observation(spec, 41)
    book.put(41, Appraised(read, KB_RESULT, 'slow'))
    facts = facts_of(spec, 41)
    value = BookAppraiser(book).appraise(facts)
    assert value is not None
    assert value.verdict == 'slow'
    assert value.band is not None
    assert value.band.q1 == 0.6
    assert BookAppraiser(book).appraise(replace(facts, unit_id=42)) is None  # no appraisal: S8


def test_the_book_appraiser_judges_a_plain_base_by_its_facts():
    facts = facts_of(case_item('white_plain_0os_monarch_left'), 7)
    value = BookAppraiser(Book()).appraise(facts)
    assert value is not None
    assert value.worth_ist is None


def test_carried_facts_take_the_identify_workers_read():
    book = Book()
    spec = case_item('goblin_toe_first_copy_is_kept')
    book.put(41, Appraised(observation(spec, 41), KB_RESULT, 'slow'))
    assert facts_of(spec).txt is not None
    item = carried(41, facts_of(spec).txt or 0, 7)
    facts = carried_facts(item, Owner.LOOP, book)
    assert (facts.name, facts.owner, facts.where) == ('Goblin Toe', Owner.LOOP, Where.INVENTORY)
    assert carried_facts(replace(item, unit_id=43), Owner.LOOP, book).name is None


def test_the_result_appraiser_asks_the_lookup_and_keeps_on_its_failure():
    facts = facts_of(case_item('goblin_toe_first_copy_is_kept'))
    value = ResultAppraiser(lambda read: KB_RESULT, lambda result, read: 'vendor').appraise(facts)
    assert value is not None
    assert value.verdict == 'vendor'

    def failing(read):
        raise TimeoutError('the retrieval process is busy')

    assert ResultAppraiser(failing).appraise(facts) is None
    assert ResultAppraiser(lambda read: KB_RESULT).appraise(replace(facts, observation=None)) is None


def test_the_fake_appraiser_and_copies_look_up_by_unit_then_name_then_code():
    facts = facts_of(case_item('goblin_toe_first_copy_is_kept'), 5)
    by_name = FakeAppraiser({'Goblin Toe': Price(0.5, 'slow'), facts.code: Price(9.0, 'sell')}).appraise(facts)
    assert by_name is not None
    assert by_name.worth_ist == 0.5
    by_unit = FakeAppraiser({5: Price(2.0, 'sell'), 'Goblin Toe': Price(0.5)}).appraise(facts)
    assert by_unit is not None
    assert by_unit.worth_ist == 2.0
    assert FakeAppraiser({}).appraise(facts) is None
    assert TableCopies({facts.code: []}).copies(facts) == []
    assert TableCopies({}).copies(facts) is None


def test_the_live_assessor_reads_nothing_until_asked():
    found = live()
    assert isinstance(found.appraiser, BookAppraiser)
    assert isinstance(found.copies, CollectionCopies)
    assert found.counted is loot_value.owned_bases


def test_the_result_appraisers_verdict_is_the_identify_workers_by_default():
    """D4 (rca/2026-10-23/assess-sites-findings.md): a reviewed high leveling use turns a triage `vendor` into `check`
    (identify/service.py `assessed_verdict`), as BOOK holds it live; the triage's own verdict only when asked."""
    facts = facts_of(case_item('goblin_toe_first_copy_is_kept'))
    recorded = next(read['result'] for read in REPLAYED if read['result']['triage'].get('verdict') == 'vendor')
    leveling = {'tier': 'high', 'reason': 'Top leveling boots. Fast run walk.'}
    result = {**recorded, 'assessment': {'leveling': [leveling]}}
    value = ResultAppraiser(lambda read: result).appraise(facts)
    assert value is not None
    assert value.verdict == 'check'
    assert value.verdict == verdict_for(result, None, facts.observation)[0]
    triage = ResultAppraiser(lambda read: result, triage_verdict).appraise(facts)
    assert triage is not None
    assert triage.verdict == 'vendor'


def test_a_vendor_sale_never_says_sell():
    """R3: the card's `sell` is the triage's trade verdict; the entry point's sale to a vendor is VENDOR."""
    assert 'sell' not in {outcome.value for outcome in Outcome}


# -- runewords (D12, 2026-10-23) ---------------------------------------------------------------------------------

CORPUS = Path(__file__).resolve().parents[3] / 'inventory_tracking' / 'corpus' / 'data' / 'items.jsonl'
RUNEWORDS = [
    record['observation']
    for record in map(json.loads, CORPUS.read_text().splitlines())
    if (record.get('observation') or {}).get('item', {}).get('runeword')
]


def test_the_corpus_holds_the_runewords():
    names = {read['item']['runeword'] for read in RUNEWORDS}
    assert {'Insight', 'Authority', 'Spirit', 'Lore', 'White', 'Fortitude'} <= names


@pytest.mark.parametrize('read', [pytest.param(read, id=f'{read["item"]["runeword"]}-{n}')
                                  for n, read in enumerate(RUNEWORDS)])  # fmt: skip
@pytest.mark.parametrize('site', [Site.FIELD, Site.TOWN, Site.GAMBLE, Site.CARD, Site.CORPUS])
@pytest.mark.parametrize('price', [Price(0.05, 'vendor'), Price(None, None), Price(0.5, 'slow')])
def test_a_runeword_is_never_given_up(read, site, price):
    """The 2B agent's corpus run: 17 of 20 runewords came out VENDOR, judged as plain bases (Insight and Authority by
    K9). A runeword is kept by K1 at every site, whatever its base's price; the last guard refuses it too."""
    facts = loot_value_facts(read)
    assert facts.runeword == read['item']['runeword']
    found = Assessor(FakeAppraiser({}, price), TableCopies({}, [])).assess(facts, site)
    assert not found.gives_up, found.said()
    assert found.rule != NEVER_TRASH, found.said()  # the rules keep it, not the guard
    assert never_trash(Assessment(facts, site, Outcome.VENDOR, 'K9', 'a test')) is not None
    assert base_floor.facts_junk(facts) is None
    assert base_floor.town_junk(facts) is None


def loot_value_facts(read: Mapping[str, Any]) -> ItemFacts:
    from inventory_tracking.loot.facts import from_observation

    return from_observation(read, where=Where.INVENTORY, owner=Owner.LOOP)


@pytest.mark.parametrize('read', [pytest.param(read, id=f'{read["item"]["runeword"]}-{n}')
                                  for n, read in enumerate(RUNEWORDS)])  # fmt: skip
@pytest.mark.parametrize('quality', [2, 3])
def test_the_game_flag_keeps_a_carried_or_ground_runeword(read, quality):
    """D12's game flag (items/identity.py RUNEWORD_FLAG, read into Carried.runeword and Rolls.runeword by
    game/decode.py): a carried runeword with no identify read is kept at every site, and one on the ground is picked
    as a must-have; without the flag the facts name no runeword."""
    found_base = base_of_code(read['item']['base_code'])
    assert found_base is not None
    txt = found_base[0]
    item = Carried(9, txt, 0, 0, (2, 3), quality=quality, identified=True, runeword=True)
    facts = from_carried(item, owner=Owner.LOOP)
    assert facts.runeword == BY_FLAG
    assert from_carried(replace(item, runeword=False), owner=Owner.LOOP).runeword is None
    assert from_carried(item, owner=Owner.LOOP, observation=read).runeword == read['item']['runeword']
    for site in (Site.FIELD, Site.TOWN, Site.GAMBLE, Site.CARD, Site.CORPUS):
        got = Assessor(FakeAppraiser({}, Price(0.05, 'vendor')), TableCopies({}, [])).assess(facts, site)
        assert not got.gives_up, got.said()
    drop = Drop(9, 0.0, 0.0, 'a base', VALUABLE, (2, 3), prized=False, source='shown', txt=txt, quality=quality,
                rolls=Rolls(4, defense=0, damage=0, runeword=True))  # fmt: skip
    ground = from_drop(drop)
    assert ground.runeword == BY_FLAG
    got = Assessor(NO_PRICES).assess(ground, Site.GROUND)
    assert got.sure, got.said()
    assert got.ground is not None
    assert got.ground.must_have, got.said()
    assert from_drop(replace(drop, rolls=Rolls(4, defense=0, damage=0))).runeword is None
