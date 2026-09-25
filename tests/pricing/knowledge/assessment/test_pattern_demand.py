from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.guide_demand import demand_for_item
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_magic_amulet_demand_requires_whole_skill_combination():
    document = build()
    profiles = document['profiles']
    item = replace(
        facts('Amulet', 'magic'),
        stats={
            '188:9': {'status': 'decoded', 'value': 3},
            '105:0': {'status': 'decoded', 'value': 10},
        },
    )

    def demand(candidate):
        return demand_for_item('Unidentified magic title', assess_roles(candidate, profiles), document)

    result = demand(item)
    assert result['scope'] == 'matched_patterns'
    assert result['distinct_builds'] == 2
    assert result['builds'] == ['lightning-sorceress', 'nova-sorceress-guide']
    assert result['grade'] == 'Pending'
    no_cast = replace(item, stats={'188:9': {'status': 'decoded', 'value': 3}})
    assert demand(no_cast)['builds'] == ['lightning-sorceress']
    cold = replace(
        item,
        stats={
            '188:10': {'status': 'decoded', 'value': 1},
            '105:0': {'status': 'decoded', 'value': 10},
        },
    )
    assert demand(cold)['builds'] == ['blizzard-sorceress']
    assert demand(replace(item, rarity='rare')) is None
    assert demand(replace(item, stats={})) is None
    assert demand_for_item(None, [], document) is None
    roles = assess_roles(item, profiles)
    assert demand_for_item(None, roles + roles, document) == result
    assert demand_for_item(None, roles, {'profiles': profiles}) is None


def test_pattern_review_cannot_pool_another_configuration_or_changed_predicate():
    from copy import deepcopy

    import pytest

    from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand

    document = build()
    row = next(r for r in document['guide_demand']['uses'] if r.get('pattern') == 'nova-starter-amulet')
    changed = {**row, 'pattern': 'lightning-starter-amulet'}
    with pytest.raises(ValueError, match='exact reviewed configuration'):
        compile_demand([changed], document['profiles'])
    profiles = deepcopy(document['profiles'])
    profile = next(p for p in profiles if p['id'] == row['profile_id'])
    profile['must']['all'].pop()
    with pytest.raises(ValueError, match='Stale'):
        compile_demand([row], profiles)


def test_pattern_summary_labels_candidate_combinations_and_excludes_unknown_rules():
    from inventory_tracking.appraisal.build_use_summary import build_use_summary

    document = build()
    item = replace(
        facts('Amulet', 'magic'),
        stats={
            '188:9': {'status': 'decoded', 'value': 3},
            '105:0': {'status': 'decoded', 'value': 10},
        },
    )
    roles = assess_roles(item, document['profiles'])
    demand = demand_for_item(None, roles, document)
    summary = build_use_summary(roles, demand)
    assert 'matching configurations' in summary.lines[0]
    assert len(summary.lines) <= 8
    unknown = [{**r, 'rule_trace': {'truth': 'unknown'}} for r in roles]
    assert demand_for_item(None, unknown, document) is None
    failed = [{**r, 'status': 'failed'} for r in roles]
    assert demand_for_item(None, failed, document) is None

    absent_trace = [{**r, 'rule_trace': None} for r in roles]
    assert demand_for_item(None, absent_trace, document) is None


def test_rare_ring_demand_counts_builds_once_and_retains_combination_gates():
    document = build()
    values = {'105:0': 10, '9:0': 20, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10, '80:0': 5}
    item = replace(
        facts('Ring', 'rare'), stats={key: {'status': 'decoded', 'value': value} for key, value in values.items()}
    )

    def demand(candidate):
        return demand_for_item('Random rare title', assess_roles(candidate, document['profiles']), document)

    result = demand(item)
    assert result is not None
    assert result['distinct_builds'] == 3
    assert len(result['patterns']) == 5
    assert len(result['contexts']) == 5
    assert result['grade'] == 'Pending'
    # Two Blizzard variants and two Lightning variants do not become extra builds.
    assert result['builds'] == ['blizzard-sorceress', 'lightning-sorceress', 'nova-sorceress-guide']
    no_fire = replace(item, stats={key: value for key, value in item.stats.items() if key not in {'39:0', '45:0'}})
    reduced = demand(no_fire)
    assert reduced['distinct_builds'] == 2
    assert 'pattern:lightning-starter-ring' not in reduced['patterns']
    assert 'pattern:nova-starter-ring' not in reduced['patterns']
    # An incomplete tri-resist capture is not a confirmed pattern match.
    incomplete = demand(replace(no_fire, capture_complete=False))
    assert 'pattern:nova-starter-ring' not in incomplete['patterns']
    assert demand(replace(item, rarity='magic')) is None
    assert demand(replace(item, stats={})) is None
    roles = assess_roles(item, document['profiles'])
    assert any(p['status'] == 'false' for r in roles for p in r.get('preferences', []))

    starter = replace(
        item,
        stats={key: {'status': 'decoded', 'value': value} for key, value in {'0:0': 5, '7:0': 10, '43:0': 10}.items()},
    )
    assert demand(starter)['patterns'] == ['pattern:blizzard-starter-ring']


def test_goldfind_base_demand_preserves_socket_preparation_and_excludes_planner_examples():
    from tests.pricing.knowledge.assessment.roles.test_goldfind_rune_swords import sword

    document = build()

    def inspect(item, context=None):
        roles = assess_roles(item, document['profiles'], context)
        return demand_for_item(None, roles, document), roles

    demand, roles = inspect(sword(), {'player_class': 'Barbarian'})
    assert demand is not None
    assert demand['distinct_builds'] == 1
    assert len(demand['patterns']) == 5
    assert all(r['dependencies'][0]['status'] == 'true' for r in roles if r['id'].endswith('lem-sword'))
    assert {c['variant'] for c in demand['contexts']} == {'Standard', 'War Cry', 'Whirlwind'}
    assert not any('leap-only' in p for p in demand['patterns'])
    empty, empty_roles = inspect(facts('Crystal Sword'), {'player_class': 'Barbarian'})
    assert empty['patterns'] == demand['patterns']
    selected = [r for r in empty_roles if 'pattern:' + r['id'] in empty['patterns']]
    assert all(r['status'] == 'partial' for r in selected)
    assert all(r['dependencies'][0]['status'] != 'true' for r in selected)
    mixed, mixed_roles = inspect(sword(['Lem Rune'] * 5 + ['Ist Rune']), {'player_class': 'Barbarian'})
    assert mixed['patterns'] == demand['patterns']
    assert all(r['dependencies'][0]['status'] == 'false' for r in mixed_roles if r['id'].endswith('lem-sword'))
    wrong = replace(sword(), sockets=3)
    assert inspect(wrong, {'player_class': 'Barbarian'})[0] is None
    assert inspect(sword(), {'player_class': 'Druid'})[0] is None
    assert inspect(sword())[0] is None  # Unknown class is not evidence of this role's fit.
    assert inspect(replace(sword(), rarity='magic'), {'player_class': 'Barbarian'})[0] is None
