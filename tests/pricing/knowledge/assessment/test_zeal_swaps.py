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
    ('name', 'base', 'quality', 'key', 'condition'),
    [
        ('Demon Limb', 'Tyrant Club', 'unique', '204:3351', 'prebuff'),
        ("Naj's Puzzler", 'Elder Staff', 'set', '204:3467', 'Enigma'),
        ('Wizardspike', 'Bone Knife', 'unique', '105:0', 'Call to Arms'),
    ],
)
def test_zeal_swap_utility_preserves_footnotes_and_charge_availability(bundle, name, base, quality, key, condition):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-footnote-swap') and r['names'] == [name]]
    assert len(roles) == 1
    role = roles[0]
    assert condition in ' '.join(role['conditions'])
    assert role['slot'] in ('Weapon-Swap', 'Prebuff')
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(
        facts(base, quality, name),
        stats={key: charged(1) if key.startswith('204:') else {'status': 'decoded', 'value': 50}},
    )

    def evaluate(item, klass='Paladin', gear=()):
        context = {
            'player_class': klass,
            'player_level': 78,
            'player_strength': 44,
            'player_dexterity': 37,
            'player_items': list(gear),
        }
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert key in evaluate(item).annotations
    if name == "Naj's Puzzler":
        assert not evaluate(item, gear=['Enigma']).annotations
    assert not evaluate(item, 'Sorceress').annotations
    assert not evaluate(replace(item, identified=False)).annotations
    if key.startswith('204:'):
        assert not evaluate(replace(item, stats={key: charged(0)})).annotations
        assert not evaluate(replace(item, stats={})).annotations
    else:
        assert 'does not' in ' '.join(role['conditions'])
        assert not evaluate(replace(item, ethereal=True)).annotations


def test_zeal_treachery_prebuff_credits_fade_not_transferred_ias(bundle):
    roles = [r for r in bundle['profiles'] if r['id'] == 'zeal-paladin-treachery-fade-prebuff']
    assert len(roles) == 1
    role = roles[0]
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(
        facts('Mage Plate', 'normal', 'Treachery'),
        runeword='Treachery',
        sockets=3,
        socket_contents='filled',
        stats={
            key: {'status': 'decoded', 'value': value}
            for key, value in [('201:17103', 5), ('93:0', 45), ('99:0', 20), ('43:0', 30)]
        },
    )

    def evaluate(item):
        context = {'player_class': 'Paladin'}
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item).annotations) == {'201:17103'}
    assert not evaluate(replace(item, ethereal=True)).annotations
    assert not evaluate(replace(item, runeword=None)).annotations
    assert not evaluate(replace(item, socket_contents='empty')).annotations
    assert not evaluate(replace(item, sockets=2)).annotations
    assert 'not' in ' '.join(role['conditions'])
