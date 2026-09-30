from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ("Highlord's Wrath", 'Amulet', {'127:0': 1, '93:0': 20, '41:0': 35, '250:0': 30}),
    (
        "Mara's Kaleidoscope",
        'Amulet',
        {'127:0': 2, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20, '0:0': 5, '1:0': 5, '2:0': 5, '3:0': 5},
    ),
    ('Metalgrid', 'Amulet', {'31:0': 300, '39:0': 25, '41:0': 25, '43:0': 25, '45:0': 25, '19:0': 400}),
    ('Raven Frost', 'Ring', {'153:0': 1, '148:0': 20, '9:0': 40, '2:0': 15, '19:0': 150}),
    ('Nagelring', 'Ring', {'80:0': 15, '19:0': 50, '35:0': 3}),
    ('Dwarf Star', 'Ring', {'142:0': 15, '35:0': 12, '7:0': 40, '79:0': 100}),
    ('Wisp Projector', 'Ring', {'144:0': 10, '80:0': 10}),
]


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(('name', 'base', 'values'), CASES)
def test_zeal_jewelry_native_benefits_and_impossible_facets(bundle, name, base, values):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-jewelry') and r['names'] == [name]]
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    if '250:0' in stats:
        stats['250:0'].update(viewer_level=80, raw=3, per_level={'numerator': 3, 'denominator': 8})
    item = replace(facts(base, 'unique', name), stats=stats)

    def evaluate(item, context):
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item, {'player_class': 'Paladin'}).annotations) == set(values)
    for context in ({'player_class': 'Necromancer'}, {}):
        assert not evaluate(item, context).annotations
    for patch in ({'sockets': 1}, {'ethereal': True}, {'identified': False}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **patch), {'player_class': 'Paladin'}).annotations
