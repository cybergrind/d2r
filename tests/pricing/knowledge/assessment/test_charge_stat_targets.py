from dataclasses import replace

import pytest

from pricing.knowledge.assessment.stat_bundle import configuration_from_row, configuration_row
from pricing.knowledge.assessment.stat_evaluation import StatPriority
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.assessment.test_stat_evaluation import configuration, evaluate


def charged(count):
    return {
        'status': 'decoded',
        'unit': 'charges_remaining',
        'value': count,
        'charges': {'remaining': count, 'maximum': 20},
    }


def teleport_config():
    predicate = {'op': 'charge_skill', 'skill_id': 54, 'value': 1}
    return replace(
        configuration(required=predicate),
        types=('amul',),
        priorities=(StatPriority('charge:54', 'desirable', predicate, 'Available Teleport charges'),),
    )


def test_charge_target_resolves_only_valid_available_matching_skill_rows():
    config = teleport_config()
    item = replace(
        facts('Amulet', 'rare'),
        stats={
            '204:3457': charged(0),
            '204:3467': charged(1),
            '204:3468': charged(2),
            '204:3079': charged(3),
        },
        gaps=['Duplicate native stat 204:3468.'],
    )
    result = evaluate(item, [config])
    assert set(result.annotations) == {'204:3467'}
    assert result.annotations['204:3467']['roll_quality'] == 'unassessed'
    assert not evaluate(replace(item, stats={'204:3457': charged(0)}), [config]).annotations
    malformed = replace(item, stats={'204:3467': {**charged(1), 'value': 2}})
    assert not evaluate(malformed, [config]).annotations
    assert configuration_from_row(configuration_row(config)) == config


@pytest.mark.parametrize('key', ['charge:-1', 'charge:4096', 'charge:054', 'charge:abc', 'charge:54:1'])
def test_charge_target_rejects_malformed_skill_selectors(key):
    with pytest.raises(ValueError, match='charged-skill target'):
        StatPriority(key, 'desirable', {'op': 'charge_skill', 'skill_id': 54, 'value': 1}, 'Teleport')


def test_reviewed_teleport_amulets_require_class_and_available_charges_in_report():
    import json

    from inventory_tracking.appraisal.stat_markers import stat_line
    from pricing.knowledge.assessment.build_profiles import ROOT, build
    from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
    from pricing.knowledge.assessment.profiles import assess_role_results
    from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator

    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id.endswith('-teleport-amul')
    ]
    assert len(configs) == 2
    for quality in ('magic', 'rare'):
        item = replace(facts('Amulet', quality), stats={'204:3457': charged(1)})
        for klass in ('Barbarian', 'Necromancer', 'Sorceress', None):
            context = {'player_class': klass} if klass else {}
            result = StatsEvaluator().evaluate(
                item, configs, context=context, role_outcomes=assess_role_results(item, profiles, context)
            )
            if klass in ('Barbarian', 'Necromancer'):
                assert set(result.annotations) == {'204:3457'}
                assert len(result.annotations['204:3457']['configuration_ids']) == 1
                line = stat_line(
                    {
                        'status': 'decoded',
                        'text': 'Level 1 Teleport (1/20 Charges)',
                        'memory_stat': {'id': 204, 'layer': 3457},
                    },
                    result.annotations,
                )
                assert '[desirable]' in line.text
            else:
                assert not result.annotations
