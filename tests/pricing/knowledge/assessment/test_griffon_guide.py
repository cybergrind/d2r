from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('fist-of-the-heavens-paladin', 2, 'Paladin', 'either'),
    ('lightning-fury-amazon-guide', 1, 'Amazon', 'thunder'),
    ('lightning-fury-amazon-guide', 2, 'Amazon', 'thunder'),
    ('lightning-fury-amazon-guide', 3, 'Amazon', 'thunder'),
    ('lightning-sentry-assassin', 1, 'Assassin', 'thunder'),
    ('lightning-sentry-assassin', 2, 'Assassin', None),
    ('lightning-sorceress', 1, 'Sorceress', 'thunder'),
    ('lightning-sorceress', 2, 'Sorceress', 'thunder'),
    ('lightning-sorceress', 3, 'Sorceress', 'facet'),
    ('lightning-strike-amazon', 1, 'Amazon', 'thunder'),
    ('lightning-strike-amazon', 2, 'Amazon', 'facet'),
    ('nova-sorceress-guide', 1, 'Sorceress', 'thunder'),
    ('nova-sorceress-guide', 2, 'Sorceress', 'thunder'),
    ('nova-sorceress-guide', 3, 'Sorceress', 'thunder'),
]


def child(kind):
    return {
        'unit_id': 100,
        'position': 0,
        'name': "Guardian's Thunder" if kind in ('thunder', 'either') else 'Rainbow Facet',
        'item_type': 'cjwl' if kind in ('thunder', 'either') else 'jewl',
        'stats_complete': True,
        'stats': {
            k: {'status': 'decoded', 'value': 5 if kind in ('thunder', 'either') else 3} for k in ['330:0', '334:0']
        },
    }


@pytest.mark.parametrize(('slug', 'index', 'cls', 'filler'), MEMBERS)
def test_griffon_minimum_rolls_keep_lightning_use_and_actual_socket_kind(slug, index, cls, filler):
    b = build()
    rid = f'{slug}-{index}-griffon-eye'
    r = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert r is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    bonus = 5 if filler in ('thunder', 'either') else 3 if filler else 0
    values = {'105:0': 25, '127:0': 1, '330:0': 10 + bonus, '334:0': 15 + bonus, '31:0': 150}
    item = replace(
        facts('Diadem', 'unique', "Griffon's Eye"),
        sockets=1 if filler else 0,
        socket_contents='filled' if filler else 'empty',
        socket_items=[child(filler)] if filler else [],
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls}

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [r], ctx)
        )

    assert len(evaluate().annotations) == 5
    assert evaluate().annotations['334:0']['desirability'] == 'desirable'
    for changes in [
        {'identified': None},
        {'ethereal': True},
        {'rarity': 'rare'},
        {'base_code': facts('Circlet').base_code},
    ]:
        assert not evaluate(replace(item, **changes)).annotations
    if filler:
        assert not evaluate(replace(item, socket_items=[])).annotations
        wrong = child(filler)
        wrong['stats']['334:0']['value'] = 0
        assert not evaluate(replace(item, socket_items=[wrong])).annotations
    if filler == 'either':
        assert evaluate(replace(item, socket_items=[child('facet')])).annotations
        assert any('table' in c and 'planner' in c for c in r['conditions'])


def test_griffon_demand_counts_builds_not_variants():
    assert build()['guide_demand']['summaries']["Griffon's Eye"]['distinct_builds'] == 6
