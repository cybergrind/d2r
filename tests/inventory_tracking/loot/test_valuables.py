"""The named acceptance table of the loot design (inventory_tracking/loot/design.md §6): every very valuable item, the
duplicates rules, the never-touch rules and the ground leave cases, one case per row of fixtures/valuables.json.

Each case runs against the new layers (`ground_judge.judge`, `keep.decide`) and against today's functions
(`loot/today.py`: pickmode.sure, junk_of, keep_copy, amulet_keeper, as the live loop composes them). A case today's
code fails is a strict xfail naming why, so a fix that lands shows up as an XPASS.
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.game.kept import PutDown
from inventory_tracking.game.records import VALUABLE, Drop, Loot
from inventory_tracking.loot import today, value as loot_value
from inventory_tracking.loot.api import droppable, town_verdicts
from inventory_tracking.loot.facts import (
    MAGIC,
    ItemFacts,
    Owner,
    Where,
    base_of_code,
    from_observation,
    quality_of,
)
from inventory_tracking.loot.ground_judge import judge
from inventory_tracking.loot.keep import Action, decide, decide_all
from inventory_tracking.loot.value import Band, Value, assess
from inventory_tracking.macros.town import BER, rune_transmutes


FIXTURE = Path(__file__).parent / 'fixtures' / 'valuables.json'
CASES = json.loads(FIXTURE.read_text())['cases']
LIFE = 7  # maxhp, kept in 256ths
KEPT = {Action.KEEP: 'kept', Action.NEVER_TOUCH: 'kept', Action.DROP: 'given up', Action.SELL: 'given up'}
EXPECTED = {'keep': 'kept', 'never-touch': 'kept', 'drop': 'given up', 'sell': 'given up', 'identify': 'identify'}


def observation(spec: dict[str, Any], unit: int) -> dict[str, Any]:
    """An identify read of the fixture item: its rolls as decoded stats, each with its roll range when given."""
    ranges = spec.get('ranges', {})
    rows = []
    for key, raw in spec.get('rolls', {}).items():
        stat, layer = (int(part) for part in key.split(':'))
        shown = raw >> 8 if stat == LIFE else raw
        memory = {'id': stat, 'layer': layer, 'raw': raw}
        row: dict[str, Any] = {'status': 'decoded', 'name': f'stat {key}', 'value': shown,
                               'text': f'stat {key} {shown}', 'memory_stat': memory}  # fmt: skip
        if key in ranges:
            row['roll_range'] = {'min': ranges[key][0], 'max': ranges[key][1], 'better': 'higher'}
        rows.append(row)
    return {
        'item': {'name': spec.get('name') or spec['base'], 'base_name': spec['base'], 'base_code': spec['code'],
                 'rarity': spec['quality'], 'identified': spec.get('identified', True),
                 'ethereal': spec.get('ethereal', False), 'sockets': spec.get('sockets', 0)},
        'source': {'unit_id': unit},
        'decoded_stats': rows,
    }  # fmt: skip


def facts_of(spec: dict[str, Any], unit: int = 1, *, owner: Owner | None = None) -> ItemFacts:
    found = from_observation(
        observation(spec, unit),
        where=Where(spec.get('where', 'inventory')),
        owner=owner or Owner(spec.get('owner', 'loop')),
        size=(spec['size'][0], spec['size'][1]) if 'size' in spec else None,
    )
    return replace(found, unit_id=unit)


def ground_facts(case: dict[str, Any]) -> ItemFacts:
    """The item as it lies (rca/2026-10-20/loot-m0-research.md): magic and better unidentified, no affix and no socket
    count read (R1); white bases with their rolls, enhanced defense included (R2: the ground read takes the ED from
    the +0xD0 chain since 2026-10-20; only knif/shie/ashd are read until M5 widens the types); no rolls when the case
    says unread."""
    found = replace(
        facts_of(case['item']), where=Where.GROUND, owner=Owner.UNKNOWN, marked=case['item'].get('marked', False)
    )
    if 'ground_rolls' in case:
        return replace(found, rolls=None, sockets=None, ethereal=None, known=None)
    if found.quality >= MAGIC:
        # R1: an unidentified item holds no affix and no socket count; only its ethereal flag is read
        return replace(found, identified=False, rolls={}, known=frozenset(), sockets=None, name=None)
    return found


def value_of(case: dict[str, Any], facts: ItemFacts) -> Value:
    given = case.get('value', {'worth': None, 'verdict': None})
    band = given.get('band')
    found = Band(band['q1'], band['median'], band.get('sellers'), band.get('observed')) if band else None
    return assess(facts, worth=given['worth'], verdict=given['verdict'], band=found)


def owned_of(case: dict[str, Any]) -> list[ItemFacts] | None:
    if case['owned'] is None:
        return None
    return [
        facts_of({**case['item'], **override}, 100 + index, owner=Owner.PLAYER)
        for index, override in enumerate(case['owned'])
    ]


def counted(case: dict[str, Any]):
    """The owned count a row with `keep_up_to` reads (live: loot/value.py `owned_bases`): the case's owned copies."""
    owned = case['owned']
    return lambda facts: None if owned is None else len(owned)


def params(aspect: str, path: str) -> list:
    found = []
    for case in CASES:
        if aspect not in case['expect']:
            continue
        fails = case.get('today_fails', {}).get(aspect) if path == 'today' else None
        marks = [pytest.mark.xfail(strict=True, reason=fails)] if fails else []
        found.append(pytest.param(case, id=case['id'], marks=marks))
    return found


@pytest.mark.parametrize('case', params('ground', 'new'))
def test_the_new_ground_judge_picks_or_leaves_each_valuable(case):
    verdict = judge(ground_facts(case), owned=counted(case))
    expect = case['expect']
    assert verdict.pick == (expect['ground'] == 'pick'), f'{case["id"]}: {verdict.said()} ({case["source"]})'
    if verdict.pick and 'then' in expect:
        assert verdict.then is not None, verdict.said()
        assert verdict.then.value == expect['then'], verdict.said()
    if 'must_have' in expect:
        assert verdict.must_have == expect['must_have'], verdict.said()


@pytest.mark.parametrize('case', params('ground', 'today'))
def test_todays_good_pickup_picks_or_leaves_each_valuable(case, monkeypatch):
    monkeypatch.setattr(loot_value, 'owned_bases', counted(case))  # never the host's collection
    verdict = today.judge(ground_facts(case))
    assert verdict.pick == (case['expect']['ground'] == 'pick'), f'{case["id"]}: {verdict.said()}'


@pytest.mark.parametrize('case', params('decision', 'new'))
def test_the_new_keep_decision_on_each_valuable(case):
    facts = facts_of(case['item'])
    decision = decide(facts, value_of(case, facts), owned_of(case))
    expect = case['expect']
    why = f'{case["id"]}: {facts.title()}: {decision.said()} ({case["source"]})'
    assert decision.action.value == expect['decision'], why
    if 'rule' in expect:
        assert decision.rule == expect['rule'], why
    for word in expect.get('reason_has', ()):
        assert word in decision.reason, why


@pytest.mark.parametrize('case', params('decision', 'today'))
def test_todays_town_judgement_on_each_valuable(case):
    facts = facts_of(case['item'])
    decision = today.decide(facts, value_of(case, facts), owned_of(case))
    outcome = KEPT.get(decision.action, decision.action.value)
    assert outcome == EXPECTED[case['expect']['decision']], f'{case["id"]}: {decision.said()}'


@pytest.mark.parametrize('case', params('field', 'new'))
def test_the_field_check_puts_down_only_a_surplus_big_set_or_unique_item(case):
    """G18 (loot/api.py, the player 2026-10-20 ~13:28: "identify a big items in the middle of the run ... and probably
    drop them without bringing to the town"): the decision, then the field's guard with the owned copies."""
    facts = facts_of(case['item'])
    value, owned = value_of(case, facts), owned_of(case)
    decision = decide(facts, value, owned)
    refused = droppable(facts, value, owned) if decision.action == Action.DROP else 'kept by the decision'
    outcome = 'drop' if refused is None else 'keep'
    assert outcome == case['expect']['field'], f'{case["id"]}: {decision.said()}; {refused} ({case["source"]})'


@pytest.mark.parametrize('case', params('town', 'new'))
def test_the_town_decision_sells_only_what_the_keep_rules_and_the_guards_give_up(case):
    """M6 (loot/keep.py TOWN_DECIDES; the player, 2026-10-20 16:55: "go ahead with the merge agent"): the town's one
    decision (loot/api.py `town_verdicts`) on the item with its owned copies."""
    facts = facts_of(case['item'])
    owned = owned_of(case)
    [verdict] = town_verdicts([(facts, value_of(case, facts))], lambda _facts: owned)
    outcome = 'sell' if verdict.sold else 'keep'
    assert outcome == case['expect']['town'], f'{case["id"]}: {verdict.said()} ({case["source"]})'


def test_every_fixture_names_its_base_by_the_game_datas_code_and_says_its_source():
    for case in CASES:
        item = case['item']
        found = base_of_code(item['code'])
        assert found is not None, case['id']
        assert found[1]['name'] == item['base'], case['id']
        assert quality_of(item['quality']), case['id']
        assert case['source'], case['id']
    assert len({case['id'] for case in CASES}) == len(CASES)


GOBLIN = {'base': 'Light Plated Boots', 'code': 'tbt', 'quality': 'unique', 'name': 'Goblin Toe',
          'ranges': {'16:0': [50, 60]}}  # fmt: skip


def test_two_copies_in_one_visit_best_first():
    # 56 % and 50 % carried, 53 % owned: the 56 % is kept (better than the owned), then counts as owned for the 50 %
    worse, best = facts_of({**GOBLIN, 'rolls': {'16:0': 50}}, 1), facts_of({**GOBLIN, 'rolls': {'16:0': 56}}, 2)
    owned = [facts_of({**GOBLIN, 'rolls': {'16:0': 53}}, 3, owner=Owner.PLAYER)]
    items = [(worse, assess(worse, worth=0.65, verdict='slow')), (best, assess(best, worth=0.85, verdict='slow'))]
    decided = {facts.unit_id: decision for facts, _, decision in decide_all(items, lambda facts: owned)}
    assert decided[2].action == Action.KEEP
    assert decided[2].rule == 'K6'
    assert decided[1].action == Action.DROP
    assert '53, 56' in decided[1].reason


def test_a_ber_rune_is_never_in_a_transmute():
    counts = dict.fromkeys(range(610, 660), 99)  # every rune and gem stack full, the Ber Runes too
    assert all(step.txt != BER and step.gem != BER for step in rune_transmutes(counts, most=50))


def test_an_item_the_loop_put_down_is_not_picked_up_again_this_game():
    game = ('game-1', 7)
    put = PutDown()
    put.see(Loot(game=game, carried=frozenset({11})))  # carried this game
    lying = Drop(11, 100.0, 200.0, 'Goblin Toe', VALUABLE, (2, 2), source='named', txt=342, quality=7)
    assert put.see(Loot(drops=(lying,), game=game, classes=((11, 342),))).drops == ()
    again = replace(lying, unit_id=12)  # streamed back with a new unit id, at the same place
    assert put.see(Loot(drops=(again,), game=game, classes=((12, 342),))).drops == ()


def test_an_own_use_claw_over_its_cap_is_sold_in_town():
    """O1 (loot/build_wants.py own-claw-white-plus3-traps, the player 2026-10-20 ~21:05): two kept, a third copy
    carried (left on the ground once two are owned; carried when the count missed it) is given up by keep.py K6 and,
    appraised vendor with no market row taking it, sold."""
    case = next(case for case in CASES if case['id'] == 'claw_own_trap_death_sentry_third_copy_given_up')
    facts = facts_of(case['item'])
    owned = owned_of(case)
    [verdict] = town_verdicts([(facts, value_of(case, facts))], lambda _facts: owned)
    assert verdict.decision is not None
    assert verdict.decision.rule == 'K6'
    assert verdict.sold, verdict.said()
