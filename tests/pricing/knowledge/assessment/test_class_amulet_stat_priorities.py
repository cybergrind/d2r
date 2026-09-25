import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_class_amulet_markers_require_class_tree_and_suffix_without_pooling():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    ids = {
        p['id']
        for p in profiles
        if 'amul' in p.get('types', []) and ('cunning-' in p['id'] or p['id'].endswith('-venomous'))
    }
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id in ids]
    assert len(configs) == 6
    for config in configs:
        necro = config.role_id.endswith('-venomous')
        skill = '188:17' if necro else '188:48'
        context = {'player_class': 'Necromancer' if necro else 'Assassin'}
        values = {skill: 3}
        if config.role_id.endswith('-whale'):
            values['7:0'] = 81
        elif config.role_id.endswith('-apprentice'):
            values['105:0'] = 10

        def evaluate(values, context=None, config=config, **changes):
            item = replace(
                facts('Amulet', 'magic'),
                stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
                **changes,
            )
            return StatsEvaluator().evaluate(
                item, [config], context=context, role_outcomes=assess_role_results(item, profiles, context)
            )

        assert not evaluate(values).annotations
        assert not evaluate(values, {'player_class': 'Barbarian'}).annotations
        result = evaluate(values, context)
        assert set(result.annotations) == set(values)
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
        for key in values:
            assert not evaluate({**values, key: values[key] - 1}, context).annotations
        assert not evaluate(
            {k: v for k, v in values.items() if k != skill}, context, capture_complete=False
        ).annotations
        assert not evaluate(values, context, rarity='rare').annotations
        assert not evaluate(values, context, ethereal=True).annotations
