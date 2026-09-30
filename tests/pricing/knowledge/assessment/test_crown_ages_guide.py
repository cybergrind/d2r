from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_counted_socket_jewels import jewel
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'index', 'cls'), [('meteor-sorceress', 4, 'Sorceress'), ('smite-paladin', 2, 'Paladin')]
)
def test_crown_ages_keeps_two_socket_setup_and_native_minimum_rolls(slug, index, cls):
    bundle = build()
    rid = f'{slug}-{index}-crown-ages'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Corona', 'unique', 'Crown of Ages'),
        sockets=2,
        socket_contents='filled',
        socket_items=[jewel(100, 0), jewel(101, 1)],
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [
                ('36:0', 10),
                ('99:0', 30),
                ('127:0', 1),
                ('39:0', 20),
                ('41:0', 20),
                ('43:0', 20),
                ('45:0', 20),
            ]
        },
    )
    context = {'player_class': cls}

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert len(evaluate().annotations) == 7
    assert evaluate().annotations['36:0']['desirability'] == 'desirable'
    for changes in (
        {'sockets': 1},
        {'ethereal': True},
        {'ethereal': None},
        {'rarity': 'rare'},
        {'identified': None},
        {'base_code': facts('Crown').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    if slug == 'meteor-sorceress':
        incomplete = replace(item, socket_items=[jewel(100, 0)])
        result = assess_role_results(incomplete, [role], context)[0]
        assert result.status == 'partial'
        assert not evaluate(incomplete).annotations
    else:
        assert any('Ber' in c and "Protector's Stone" in c for c in role['conditions'])
    assert bundle['guide_demand']['summaries']['Crown of Ages']['distinct_builds'] >= 2
    assert bundle['guide_demand']['summaries']['Crown of Ages']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['Crown of Ages']['builds'])
    )
