import json
from dataclasses import replace

import pytest

from inventory_tracking.appraisal.stat_markers import stat_line
from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'klass'),
    [
        ('smite-paladin-starter-charges-82', 'Paladin'),
        ('dragon-talon-assassin-budget-charges-82', 'Assassin'),
        ('dream-paladin-ubers-charges-82', 'Paladin'),
    ],
)
def test_life_tap_markers_require_available_charges_and_source_context(role, klass):
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == role)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    context = {'player_class': klass, 'player_items': []}
    key = f'204:{82 * 64 + 5}'

    def evaluate(stats, context=context, **changes):
        item = replace(facts('Bone Wand', 'magic'), stats=stats, **changes)
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [profile], context)
        )

    for quality in ('magic', 'rare'):
        for ethereal in (False, True, None):
            result = evaluate({key: charged(1)}, rarity=quality, ethereal=ethereal)
            assert set(result.annotations) == {key}
            assert result.annotations[key]['roll_quality'] == 'unassessed'
            assert result.configurations[0]['role']['status'] == 'partial'
            assert any('Ethereal' in v for v in result.configurations[0]['role']['missing'])
    line = stat_line(
        {
            'status': 'decoded',
            'text': 'Level 5 Life Tap (1/20 Charges)',
            'memory_stat': {'id': 204, 'layer': 82 * 64 + 5},
        },
        result.annotations,
    )
    assert '[desirable]' in line.text
    for stats in ({key: charged(0)}, {}, {'204:3457': charged(1)}, {key: {**charged(1), 'value': 2}}):
        assert not evaluate(stats).annotations
    assert not evaluate({key: charged(1)}, gaps=[f'Duplicate native stat {key}.']).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate({key: charged(1)}, context).annotations
    for changes in ({'rarity': 'unique'}, {'identified': False}, {'item_type': 'staf'}):
        assert not evaluate({key: charged(1)}, **changes).annotations
    if role.startswith('dream'):
        assert not evaluate({key: charged(1)}, {'player_class': klass}).annotations
        for companion in ('Last Wish', "Dracul's Grasp"):
            assert not evaluate({key: charged(1)}, {'player_class': klass, 'player_items': [companion]}).annotations
