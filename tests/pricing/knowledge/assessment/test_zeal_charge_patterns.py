from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(
    ('suffix', 'base', 'skill', 'alternative'),
    [
        ('life-tap-wand', 'Bone Wand', 82, "Dracul's Grasp"),
        ('teleport-staff', 'Gnarled Staff', 54, 'Enigma'),
        ('teleport-amulet', 'Amulet', 54, 'Enigma'),
    ],
)
def test_zeal_charges_require_availability_and_missing_alternative(bundle, suffix, base, skill, alternative):
    roles = [r for r in bundle['profiles'] if r['id'] == 'zeal-paladin-' + suffix + '-footnote']
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    key = f'204:{skill * 64 + 1}'
    item = replace(facts(base, 'magic'), stats={key: charged(1)})

    def evaluate(item, gear=(), klass='Paladin'):
        context = {'player_class': klass, 'player_items': list(gear)}
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert key in evaluate(item).annotations
    assert key in evaluate(replace(item, rarity='rare')).annotations
    assert not evaluate(replace(item, stats={key: charged(0)})).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert not evaluate(item, gear=[alternative]).annotations
    assert not evaluate(item, klass='Sorceress').annotations
    if skill == 82:
        for gear in ('Exile', 'Last Wish'):
            assert not evaluate(item, gear=[gear]).annotations
