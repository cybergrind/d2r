from dataclasses import replace

import pytest

from pricing.knowledge.assessment.stat_evaluation import StatConfiguration, StatPriority, StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def threshold(key, value):
    return {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}


def configuration(identifier='caster', required=None, tone='desirable'):
    return StatConfiguration(
        id=identifier,
        version=1,
        role_id=identifier,
        qualities=('rare',),
        types=('ring',),
        required=required or {'all': [threshold('105:0', 10), threshold('9:0', 20)]},
        priorities=(StatPriority('105:0', tone, threshold('105:0', 10), 'Cast rate for this combination'),),
        source={'path': 'reviewed/source', 'sha256': 'fixture', 'locator': '/ring'},
        review_state='reviewed',
        rationale='Explicit reviewed combination',
    )


def item(values, **changes):
    return replace(
        facts('Ring', 'rare'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
    )


def evaluate(candidate, configs, context=None):
    roles = [{'id': config.role_id, 'status': 'matched', 'dependencies': []} for config in configs]
    return StatsEvaluator().evaluate(candidate, configs, context, role_outcomes=roles)


def test_complete_combination_required_unknown_and_failed_do_not_get_markers():
    config = configuration()
    full = evaluate(item({'105:0': 10, '9:0': 20}), [config])
    assert full.annotations['105:0']['desirability'] == 'desirable'
    assert full.annotations['105:0']['roll_quality'] == 'unassessed'
    for candidate, status in [
        (item({'105:0': 10}), 'failed'),
        (item({'105:0': 10, '9:0': 19}), 'failed'),
        (item({'105:0': 10}, capture_complete=False), 'unknown'),
    ]:
        result = evaluate(candidate, [config])
        assert not result.annotations
        assert result.configurations[0]['status'] == status
    assert not evaluate(item({'105:0': 10, '9:0': 20}, rarity='magic'), [config]).configurations


def test_incomplete_uses_never_pool_and_independent_matches_keep_provenance():
    one = configuration('one', {'all': [threshold('105:0', 10), threshold('9:0', 20)]})
    two = configuration('two', {'all': [threshold('105:0', 10), threshold('7:0', 20)]}, 'supporting')
    incomplete = evaluate(item({'105:0': 10, '9:0': 10, '7:0': 10}), [one, two])
    assert not incomplete.annotations
    full = evaluate(item({'105:0': 10, '9:0': 20, '7:0': 20}), [two, one])
    assert full.annotations['105:0']['desirability'] == 'desirable'
    assert full.annotations['105:0']['configuration_ids'] == ('one', 'two')
    assert full == evaluate(item({'105:0': 10, '9:0': 20, '7:0': 20}), [one, two, one])


def test_unknown_context_unreviewed_config_and_inactive_support_stay_neutral():
    config = configuration(
        required={'all': [threshold('105:0', 10), {'op': 'context_eq', 'field': 'player_class', 'value': 'Sorceress'}]}
    )
    candidate = item({'105:0': 10})
    assert not evaluate(candidate, [config]).annotations
    assert evaluate(candidate, [config], {'player_class': 'Sorceress'}).annotations
    assert not evaluate(candidate, [replace(config, review_state='pending')], {'player_class': 'Sorceress'}).annotations
    inactive = replace(config, priorities=(StatPriority('105:0', 'supporting', threshold('9:0', 20), 'Needs mana'),))
    assert not evaluate(candidate, [inactive], {'player_class': 'Sorceress'}).annotations
    with pytest.raises(ValueError, match='reviewed positive'):
        StatPriority('105:0', 'irrelevant', threshold('105:0', 10), 'Cannot infer grey from failure')
    with pytest.raises(ValueError, match='Conflicting stat configuration'):
        evaluate(candidate, [config, replace(config, version=2)])


def test_alternatives_exclusions_and_current_socket_state_are_not_pooled():
    config = configuration(
        required={
            'all': [
                {'any': [threshold('9:0', 20), threshold('7:0', 20)]},
                threshold('105:0', 10),
                {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
            ]
        }
    )
    for values in ({'105:0': 10, '9:0': 20}, {'105:0': 10, '7:0': 20}):
        candidate = item(values)
        assert evaluate(candidate, [config]).annotations
        assert not evaluate(replace(candidate, ethereal=True), [config]).annotations
        assert not evaluate(replace(candidate, identified=False), [config]).annotations
        assert not evaluate(replace(candidate, socket_contents='filled'), [config]).annotations
    # Optional/supporting rolls cannot compensate for two incomplete alternatives.
    assert not evaluate(item({'105:0': 10, '9:0': 19, '7:0': 19, '80:0': 25}), [config]).annotations


def test_configuration_and_results_are_immutable_and_absent_rows_are_not_invented():
    required = {'all': [threshold('105:0', 10), threshold('9:0', 20)]}
    config = configuration(required=required)
    required['all'].clear()
    assert not evaluate(item({'105:0': 10}), [config]).annotations
    result = evaluate(item({'105:0': 10, '9:0': 20}), [config])
    with pytest.raises(TypeError):
        result.annotations['105:0']['desirability'] = 'irrelevant'
    absent = replace(config, priorities=(StatPriority('80:0', 'supporting', threshold('105:0', 10), 'Optional MF'),))
    assert not evaluate(item({'105:0': 10, '9:0': 20}), [absent]).annotations


def test_linked_role_outcomes_gate_current_annotations_and_retain_dependencies():
    evaluator = StatsEvaluator()
    config = configuration()
    candidate = item({'105:0': 10, '9:0': 20})
    assert not evaluator.evaluate(candidate, [config], role_outcomes=[]).annotations
    for role_status, expected in [('partial', 'conditional'), ('unknown', 'unknown'), ('failed', 'failed')]:
        role = {
            'id': config.role_id,
            'status': role_status,
            'dependencies': [{'status': 'false', 'preparation': {'action': 'clear_sockets'}}],
        }
        result = evaluator.evaluate(candidate, [config], role_outcomes=[role])
        assert not result.annotations
        assert result.configurations[0]['status'] == expected
        assert result.configurations[0]['role']['dependencies'][0]['preparation']['action'] == 'clear_sockets'
    role = {'id': config.role_id, 'status': 'matched', 'dependencies': []}
    result = evaluator.evaluate(candidate, [config], role_outcomes=[role, role])
    assert result.annotations['105:0']['desirability'] == 'desirable'
    with pytest.raises(ValueError, match='Conflicting role outcome'):
        evaluator.evaluate(candidate, [config], role_outcomes=[role, {**role, 'status': 'failed'}])


def test_reviewed_advisory_does_not_override_typed_dependencies_or_change_role_fit():
    config = replace(configuration(), advisory_conditions=('Check whole loadout',))
    candidate = item({'105:0': 10, '9:0': 20})
    role = {
        'id': config.role_id,
        'status': 'partial',
        'missing': ['Check whole loadout'],
        'failed': [],
        'rule_trace': {'truth': 'true'},
        'skill_trace': None,
        'dependencies': [],
        'equipment': None,
    }
    evaluator = StatsEvaluator()
    result = evaluator.evaluate(candidate, [config], role_outcomes=[role])
    assert result.annotations
    assert result.configurations[0]['role']['status'] == 'partial'
    assert role['status'] == 'partial'
    for changed in (
        {**role, 'dependencies': [{'status': 'unknown'}]},
        {**role, 'dependencies': [{'status': 'false', 'preparation': {'action': 'clear_sockets'}}]},
        {**role, 'missing': ['Check whole loadout', 'Needs sockets']},
        {**role, 'equipment': {'status': 'unmet'}},
        {**role, 'rule_trace': {'truth': 'unknown'}},
        {**role, 'skill_trace': {'truth': 'false'}},
    ):
        assert not evaluator.evaluate(candidate, [config], role_outcomes=[changed]).annotations
    assert not evaluator.evaluate(
        candidate, [replace(config, advisory_conditions=())], role_outcomes=[role]
    ).annotations
