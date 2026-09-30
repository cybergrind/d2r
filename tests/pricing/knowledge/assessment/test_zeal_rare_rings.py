from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RES = {'39:0': 3, '41:0': 3, '43:0': 3, '45:0': 3}


@pytest.mark.parametrize(
    ('reference', 'values'),
    [
        ('15', {'105:0': 10, '19:0': 10, '60:0': 1, '62:0': 1, **RES, '80:0': 5}),
        ('73', {'105:0': 10, '19:0': 10, '60:0': 1, '7:0': 5, **RES, '80:0': 5}),
        ('171', {'105:0': 10, '19:0': 10, '60:0': 1, **RES, '80:0': 5}),
        ('55', {'19:0': 10, '62:0': 1, '60:0': 1, '9:0': 5, '80:0': 5, **RES}),
        ('41', {'19:0': 10, '62:0': 1, '60:0': 1, **RES}),
        ('154', {'19:0': 10, '62:0': 1, '39:0': 5, '41:0': 5}),
    ],
)
def test_zeal_ring_requires_whole_reviewed_combination(reference, values):
    bundle = build()
    rid = 'zeal-paladin-rare-ring-' + reference
    roles = [r for r in bundle['profiles'] if r['id'] == rid]
    assert len(roles) == 1
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Ring', 'rare', 'Example Ring'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    )

    def evaluate(candidate, klass='Paladin'):
        ctx = {'player_class': klass}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == set(values)
    # A high isolated roll cannot compensate for a missing member of the combination.
    for key in values:
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert not evaluate(missing).annotations
    if '105:0' in values:
        assert not evaluate(replace(item, stats={**item.stats, '105:0': {'status': 'decoded', 'value': 9}})).annotations
    for patch in (
        {'rarity': 'magic'},
        {'ethereal': True},
        {'sockets': 1},
        {'base_code': facts('Amulet').base_code, 'item_type': 'amul'},
    ):
        assert not evaluate(replace(item, **patch)).annotations
    assert not evaluate(item, 'Sorceress').annotations
    assert 'Zeal attack speed' in ' '.join(roles[0]['conditions'])
