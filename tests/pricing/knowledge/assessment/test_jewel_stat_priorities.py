import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_jewel_markers_require_both_mods_and_correct_wearer_recipient():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if 'jewl' in c.types]
    assert len(configs) == 7
    for config in configs:
        player = config.role_id == 'hammer-ubers-ias-lightning-jewel'
        key = '41:0' if player else '39:0'
        recipient = "Guillaume's Face" if player else "Andariel's Visage"
        field = 'player_items' if player else 'mercenary_items'
        other = 'mercenary_items' if player else 'player_items'
        values = {'93:0': 15, key: 10}

        def evaluate(values, context=None, config=config, **changes):
            item = replace(
                facts('Jewel', 'magic'),
                stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
                **changes,
            )
            return StatsEvaluator().evaluate(
                item, [config], context=context, role_outcomes=assess_role_results(item, profiles, context)
            )

        assert not evaluate(values).annotations
        assert not evaluate(values, {other: [recipient]}).annotations
        assert not evaluate(values, {field: ['Rockstopper']}).annotations
        result = evaluate(values, {field: [recipient]})
        assert set(result.annotations) == {'93:0', key}
        assert all(a['desirability'] == 'desirable' for a in result.annotations.values())
        assert result.configurations[0]['role']['status'] == 'partial'
        assert not evaluate({'93:0': 15}, {field: [recipient]}, capture_complete=False).annotations
        assert not evaluate({**values, '93:0': 16}, {field: [recipient]}).annotations
        assert not evaluate(values, {field: [recipient]}, rarity='rare').annotations
