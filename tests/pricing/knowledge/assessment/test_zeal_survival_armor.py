from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    (
        'Crown of Ages',
        'Corona',
        1,
        {'127:0': 1, '36:0': 10, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20, '99:0': 30},
    ),
    ('Vampire Gaze', 'Grim Helm', 0, {'60:0': 6, '62:0': 6, '36:0': 15, '35:0': 10}),
    ('Rockstopper', 'Sallet', 0, {'36:0': 10, '39:0': 20, '41:0': 20, '43:0': 20, '99:0': 30, '3:0': 15}),
    ('Crown of Thieves', 'Grand Crown', 0, {'2:0': 25, '60:0': 9, '7:0': 50, '9:0': 35, '39:0': 33, '79:0': 80}),
    (
        'Harlequin Crest',
        'Shako',
        0,
        {'127:0': 2, '36:0': 10, '80:0': 50, '0:0': 2, '1:0': 2, '2:0': 2, '3:0': 2, '216:0': 120, '217:0': 120},
    ),
    ('Shaftstop', 'Mesh Armor', 0, {'32:0': 250, '36:0': 30, '7:0': 60, '16:0': 180}),
    (
        "Duriel's Shell",
        'Cuirass',
        0,
        {'0:0': 15, '214:0': 100, '216:0': 80, '16:0': 160, '39:0': 20, '41:0': 20, '43:0': 50, '45:0': 20, '153:0': 1},
    ),
]


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(('name', 'base', 'sockets', 'values'), CASES)
def test_zeal_survival_armor_preserves_legal_sockets_and_physical_recipients(bundle, name, base, sockets, values):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-survival-armor') and r['names'] == [name]]
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    for key, coefficient in [('214:0', 10), ('216:0', 12 if name == 'Harlequin Crest' else 8), ('217:0', 12)]:
        if key in stats:
            scale = 1 if key == '214:0' else 256
            stats[key].update(
                viewer_level=80,
                raw=coefficient * scale,
                per_level={'numerator': coefficient * scale, 'denominator': 8 * scale},
            )
    item = replace(facts(base, 'unique', name), sockets=sockets, stats=stats)

    def evaluate(item, klass='Paladin'):
        context = {'player_class': klass}
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(item, 'Necromancer').annotations
    for patch in [{'ethereal': True}, {'ethereal': None}, {'identified': False}, {'rarity': 'rare'}, {'sockets': 3}]:
        assert not evaluate(replace(item, **patch)).annotations
    if name == 'Crown of Ages':
        assert not evaluate(replace(item, sockets=0)).annotations
        assert set(evaluate(replace(item, sockets=2, socket_contents='filled')).annotations) == set(values)
    else:
        assert set(evaluate(replace(item, sockets=1, socket_contents='filled')).annotations) == set(values)
