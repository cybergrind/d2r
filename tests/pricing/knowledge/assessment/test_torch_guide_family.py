from dataclasses import replace

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.policies.test_torch_tier import torch


def test_reviewed_torch_family_supports_all_classes_at_native_minimum_rolls():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == ['Hellfire Torch']]
    assert len(roles) >= 67
    assert len({r['build'] for r in roles}) >= 26
    classes = set()
    for role in roles:
        cls = role['must']['all'][0]['value']
        classes.add(cls)
        item = torch(CLASS_NAMES.index(cls), 10, 10)
        context = {'player_class': cls}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert evaluate(item).annotations[f'83:{CLASS_NAMES.index(cls)}']['desirability'] == 'desirable'
        assert not evaluate(torch((CLASS_NAMES.index(cls) + 1) % 8, 20, 20)).annotations
        assert not evaluate(replace(item, identified=False)).annotations
        assert 'Hardcore' not in role['variant']
    assert classes == set(CLASS_NAMES)


def test_torch_planner_examples_are_not_promoted_to_guide_endorsements():
    bundle = build()
    uses = bundle['guide_demand']['uses']
    row = next(u for u in uses if u['profile_id'] == 'fire-blast-assassin-2-torch')
    assert row['strength'] == 'example'
    row = next(u for u in uses if u['profile_id'] == 'mirrored-blades-warlock-guide-1-torch')
    assert row['review_state'] == 'reviewed'
