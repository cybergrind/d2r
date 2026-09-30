from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs


def test_non_named_qualities_do_not_require_unique_set_tiers():
    rows = {row['id']: row for row in build_matrix(*inputs())['rows']}
    for key in ('base:base:normal', 'use:role:magic', 'use:role:rare'):
        assert rows[key]['dimensions']['named_tiers']['state'] == 'excluded'
        assert rows[key]['dimensions']['market']['state'] == 'pending'


def test_universal_baseline_closes_named_tier_and_leveling_review_only():
    data = inputs()
    data[2]['rows'][0]['status'] = 'pending'
    gate = {
        'rows': [
            {
                'quality': 'unique',
                'name': 'Unmentioned',
                'tier': 'low',
                'baseline_error': None,
                'leveling_review': 'no_specific_recommendation',
            }
        ]
    }
    result = build_matrix(*data, named_gate=gate)
    row = next(row for row in result['rows'] if row['id'] == 'identity:u')
    for key in ('named_tiers', 'leveling'):
        assert row['dimensions'][key]['state'] == 'reviewed'
        assert row['dimensions'][key]['sources'] == [{'artifact': 'named_gate', 'locator': '/rows/0'}]
    for key in ('market', 'desirability', 'stat_annotations'):
        assert row['dimensions'][key]['state'] == 'pending'
    changed = deepcopy(gate)
    changed['rows'][0]['baseline_error'] = 'unverified source'
    row = next(row for row in build_matrix(*data, named_gate=changed)['rows'] if row['id'] == 'identity:u')
    assert row['dimensions']['named_tiers']['state'] == 'blocked'


def test_multi_named_role_requires_every_named_baseline():
    data = inputs()
    data[3]['profiles'][0].update(qualities=['unique'], names=['Unmentioned', 'Other'])
    gate = {'rows': [{'quality': 'unique', 'name': 'Unmentioned', 'tier': 'low', 'baseline_error': None}]}
    row = next(row for row in build_matrix(*data, named_gate=gate)['rows'] if row['id'] == 'use:role:unique')
    assert row['dimensions']['named_tiers']['state'] == 'pending'
    gate['rows'].append({'quality': 'unique', 'name': 'Other', 'tier': 'med', 'baseline_error': None})
    row = next(row for row in build_matrix(*data, named_gate=gate)['rows'] if row['id'] == 'use:role:unique')
    assert row['dimensions']['named_tiers']['state'] == 'reviewed'
    assert len(row['dimensions']['named_tiers']['sources']) == 2


def test_unknown_quality_is_not_an_implicit_tier_exclusion():
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    row = {
        'kind': 'use_quality',
        'quality': None,
        'dimensions': {'discovery': {'sources': []}, 'named_tiers': {'state': 'pending'}},
    }
    apply_named_dimensions([row], None)
    assert row['dimensions']['named_tiers']['state'] == 'pending'


def test_named_evidence_inherits_only_exact_identity_baseline():
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    identity = {
        'id': 'identity:u',
        'kind': 'identity',
        'name': 'Unmentioned',
        'category': 'unique',
        'dimensions': {key: {'state': 'pending', 'sources': []} for key in ('discovery', 'named_tiers', 'leveling')},
    }
    evidence = {
        'id': 'evidence:r',
        'kind': 'evidence',
        'name': 'Unmentioned',
        'quality': 'unique',
        'identity_ids': ['identity:u'],
        'dimensions': {
            key: {'state': 'pending', 'sources': []}
            for key in ('discovery', 'named_tiers', 'leveling', 'market', 'desirability')
        },
    }
    gate = {'rows': [{'quality': 'unique', 'name': 'Unmentioned', 'tier': 'low'}]}
    apply_named_dimensions([identity, evidence], gate)
    assert evidence['dimensions']['named_tiers']['state'] == 'reviewed'
    assert evidence['dimensions']['named_tiers']['sources'] == [
        {'artifact': 'named_gate', 'locator': '/rows/0'},
    ]
    assert evidence['dimensions']['named_tiers']['identity_ids'] == ['identity:u']
    for key in ('leveling', 'market', 'desirability'):
        assert evidence['dimensions'][key]['state'] == 'pending'

    for changes in (
        {'identity_ids': []},
        {'identity_ids': ['missing']},
        {'identity_ids': ['identity:u', 'missing']},
        {'quality': 'set'},
        {'name': 'Other'},
        {'quality': None},
    ):
        invalid = deepcopy(evidence)
        invalid.update(changes)
        invalid['dimensions']['named_tiers'] = {'state': 'pending', 'sources': []}
        apply_named_dimensions([identity, invalid], gate)
        assert invalid['dimensions']['named_tiers']['state'] == 'pending'

    gate['rows'][0]['baseline_error'] = 'stale review'
    apply_named_dimensions([identity, evidence], gate)
    assert evidence['dimensions']['named_tiers']['state'] == 'blocked'


def test_native_non_trade_exclusion_requires_exact_catalog_identity():
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    row = {
        'id': 'identity:quest',
        'kind': 'identity',
        'name': 'Quest item',
        'category': 'unique',
        'catalog_ids': ['unique123'],
        'dimensions': {
            key: {'state': 'pending', 'sources': []} for key in ('discovery', 'named_tiers', 'leveling', 'market')
        },
    }
    entry = {
        'quality': 'unique',
        'name': 'Quest item',
        'table_id': 123,
        'kind': 'quest_item',
        'base_quest': 10,
        'native_definition': {'index': 'InternalQuestKey', '*ID': 123, 'spawnable': 1},
        'reason': 'Native quest item; no equipment trade tier.',
    }
    gate = {'rows': [], 'excluded': [entry]}
    apply_named_dimensions([row], gate)
    assert row['dimensions']['named_tiers']['state'] == 'excluded'
    assert row['dimensions']['named_tiers']['sources'] == [
        {'artifact': 'named_gate', 'locator': '/excluded/0'},
    ]
    for key in ('leveling', 'market'):
        assert row['dimensions'][key]['state'] == 'pending'
    for change in ({'catalog_ids': []}, {'catalog_ids': ['unique999']}, {'category': 'set'}):
        invalid = deepcopy(row)
        invalid.update(change)
        invalid['dimensions']['named_tiers'] = {'state': 'pending', 'sources': []}
        apply_named_dimensions([invalid], gate)
        assert invalid['dimensions']['named_tiers']['state'] == 'pending'
    for change in (
        {'base_quest': None},
        {'kind': 'unreviewed'},
        {'reason': ''},
        {'native_definition': {'index': 'Other', '*ID': 999, 'spawnable': 1}},
    ):
        invalid = deepcopy(row)
        invalid['dimensions']['named_tiers'] = {'state': 'pending', 'sources': []}
        invalid_entry = {**entry, **change}
        apply_named_dimensions([invalid], {'rows': [], 'excluded': [invalid_entry]})
        assert invalid['dimensions']['named_tiers']['state'] == 'pending'


@pytest.mark.parametrize(
    ('kind', 'native_fields', 'expected'),
    [
        ('disabled_definition', {'spawnable': 0}, 'excluded'),
        ('disabled_definition', {'spawnable': 1}, 'pending'),
        ('definition_placeholder', {}, 'excluded'),
        ('definition_placeholder', {'prop1': 'dmg%'}, 'pending'),
        ('definition_placeholder', {'spawnable': 1}, 'pending'),
    ],
)
def test_disabled_and_placeholder_tier_exclusions_check_native_facts(kind, native_fields, expected):
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    row = {
        'id': 'identity:u',
        'kind': 'identity',
        'name': 'Native',
        'category': 'unique',
        'catalog_ids': ['unique123'],
        'dimensions': {'named_tiers': {'state': 'pending'}},
    }
    gate = {
        'rows': [],
        'excluded': [
            {
                'quality': 'unique',
                'name': 'Native',
                'table_id': 123,
                'kind': kind,
                'reason': 'Native definition reviewed.',
                'native_definition': {'index': 'Native', '*ID': 123, **native_fields},
            }
        ],
    }
    apply_named_dimensions([row], gate)
    assert row['dimensions']['named_tiers']['state'] == expected


def test_captured_named_baseline_requires_matching_native_identity():
    from copy import deepcopy

    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    identity = {
        'id': 'identity:tancred',
        'kind': 'identity',
        'name': "Tancred's Crowbill",
        'category': 'set',
        'catalog_ids': ['set30'],
        'dimensions': {'named_tiers': {'state': 'pending'}},
    }
    capture = {
        'id': 'capture:item',
        'kind': 'observed_capture',
        'facts': {
            'name': "Tancred's Crowbill",
            'rarity': 'set',
            'identified': True,
            'provenance': {'capture': {'item_identity': {'table': 'set', 'table_id': 30}}},
        },
        'dimensions': {
            'named_tiers': {'state': 'pending'},
            'report': {'state': 'pending'},
            'market': {'state': 'pending'},
            'discovery': {'sources': [{'artifact': 'observed', 'locator': '/captures/0'}]},
        },
    }
    gate = {'rows': [{'quality': 'set', 'name': "Tancred's Crowbill", 'tier': 'trash'}]}
    apply_named_dimensions([identity, capture], gate)
    assert capture['dimensions']['named_tiers']['state'] == 'reviewed'
    assert capture['dimensions']['report']['state'] == 'pending'
    assert capture['dimensions']['market']['state'] == 'pending'
    for patch in ({'table_id': 31}, {'table': 'unique'}, {'mode_eligibility': 'ladder_only'}):
        invalid = deepcopy(capture)
        invalid['facts']['provenance']['capture']['item_identity'].update(patch)
        invalid['dimensions']['named_tiers'] = {'state': 'pending'}
        apply_named_dimensions([identity, invalid], gate)
        assert invalid['dimensions']['named_tiers']['state'] == 'pending'
    for field, value in (('name', 'Other item'), ('identified', False), ('provenance', {})):
        invalid = deepcopy(capture)
        invalid['facts'][field] = value
        invalid['dimensions']['named_tiers'] = {'state': 'pending'}
        apply_named_dimensions([identity, invalid], gate)
        assert invalid['dimensions']['named_tiers']['state'] == 'pending'
    gate['rows'][0]['baseline_error'] = 'Missing rendered tier'
    apply_named_dimensions([identity, capture], gate)
    assert capture['dimensions']['named_tiers']['state'] == 'blocked'


def test_captured_affixed_item_does_not_require_unique_set_baseline():
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    capture = {
        'kind': 'observed_capture',
        'facts': {'rarity': 'rare'},
        'dimensions': {
            'named_tiers': {'state': 'pending'},
            'discovery': {'sources': [{'artifact': 'observed', 'locator': '/captures/0'}]},
        },
    }
    apply_named_dimensions([capture], None)
    assert capture['dimensions']['named_tiers']['state'] == 'excluded'
