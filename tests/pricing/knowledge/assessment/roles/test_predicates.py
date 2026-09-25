from dataclasses import replace

import pytest

from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_missing_context_is_conditional_but_explicit_wrong_context_is_false():
    from pricing.knowledge.assessment.roles.predicates import evaluate

    rule = {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 5 Frenzy'}
    item = facts('Basinet')
    assert evaluate(rule, item).truth == 'unknown'
    assert evaluate(rule, item, {'mercenary_type': 'Act 2 Prayer'}).truth == 'false'
    assert evaluate(rule, item, {'mercenary_type': 'Act 5 Frenzy'}).truth == 'true'


def test_compound_rules_do_not_let_preferred_stat_replace_required_skill():
    from pricing.knowledge.assessment.roles.predicates import evaluate

    item = replace(
        facts('Diadem', 'rare'),
        stats={
            '105:0': {'status': 'decoded', 'value': 20},
            '83:1': {'status': 'decoded', 'value': 0},
        },
    )
    rule = {
        'all': [
            {'op': 'stat_at_least', 'key': '105:0', 'value': 20},
            {'op': 'stat_at_least', 'key': '83:1', 'value': 2},
        ]
    }
    result = evaluate(rule, item)
    assert result.truth == 'false'
    assert [child.truth for child in result.children] == ['true', 'false']
    assert evaluate({'any': rule['all']}, item).truth == 'true'
    assert evaluate({'not': rule}, item).truth == 'true'


def test_unknown_native_parameter_cannot_use_another_skills_value():
    from pricing.knowledge.assessment.roles.predicates import evaluate

    item = replace(facts('Diadem'), stats={'107:1': {'status': 'decoded', 'value': 3}})
    assert evaluate({'op': 'stat_at_least', 'key': '107:2', 'value': 1}, item).truth == 'unknown'


@pytest.mark.parametrize(
    'rule', [{'all': []}, {'op': 'eval', 'value': '1+1'}, {'op': 'stat_at_least', 'key': '105:0', 'value': True}]
)
def test_invalid_executable_rule_is_rejected(rule):
    from pricing.knowledge.assessment.roles.predicates import validate

    with pytest.raises(ValueError, match=r'Predicate group|Unknown predicate|Stat threshold'):
        validate(rule)


def test_new_required_rule_reaches_existing_profile_evaluation():
    from pricing.knowledge.assessment.profiles import assess_roles

    p = {
        'id': 'test',
        'types': ['circ'],
        'qualities': ['rare'],
        'build': 'test',
        'variant': 'test',
        'side': 'player',
        'slot': 'Helmet',
        'role': 'caster',
        'review_status': 'reviewed_setup',
        'source': {},
        'must': {'op': 'stat_at_least', 'key': '105:0', 'value': 20},
    }
    item = replace(facts('Diadem', 'rare'), stats={'105:0': {'status': 'decoded', 'value': 10}})
    role = assess_roles(item, [p])[0]
    assert role['status'] == 'failed'
    assert role['rule_trace']['truth'] == 'false'
    assert assess_roles(replace(item, stats={}), [p])[0]['status'] == 'partial'


@pytest.mark.parametrize(
    'rule',
    [
        {'op': 'fact_eq', 'field': 'ethereal', 'value': 'yes'},
        {'op': 'fact_eq', 'field': 'sockets', 'value': True},
        {'op': 'context_contains', 'field': 'mercenary_type', 'value': 'Act 2'},
        {'op': 'context_eq', 'field': 'player_level', 'value': float('nan')},
    ],
)
def test_predicate_fields_require_correct_value_types(rule):
    from pricing.knowledge.assessment.roles.predicates import validate

    with pytest.raises(ValueError, match=r'type|collection'):
        validate(rule)


def test_profile_rejects_parameter_on_unparameterized_stat():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.profiles import validate_profiles

    profiles = build()['profiles']
    profiles[0]['must'] = {'op': 'stat_at_least', 'key': '105:999', 'value': 20}
    with pytest.raises(ValueError, match='parameter'):
        validate_profiles(profiles)


@pytest.mark.parametrize('observed', [['Tal piece', None], ['Tal piece', 1], 'Tal piece', {'Tal piece': True}])
def test_malformed_equipment_context_is_unknown_not_a_match_or_crash(observed):
    from pricing.knowledge.assessment.roles.predicates import evaluate

    rule = {'op': 'context_contains', 'field': 'player_items', 'value': 'Tal piece'}
    assert evaluate(rule, facts('Amulet'), {'player_items': observed}).truth == 'unknown'


@pytest.mark.parametrize('observed', [False, -1, '75', 75.0])
def test_invalid_context_level_is_unknown_not_confirmed_mismatch(observed):
    from pricing.knowledge.assessment.roles.predicates import evaluate

    rule = {'op': 'context_eq', 'field': 'player_level', 'value': 75}
    assert evaluate(rule, facts('Amulet'), {'player_level': observed}).truth == 'unknown'
