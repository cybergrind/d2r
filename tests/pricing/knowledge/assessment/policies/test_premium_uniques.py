from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def item(base, name, stats, **facets):
    return replace(
        facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in stats.items()}, **facets
    )


def test_andariel_ethereal_and_joint_perfect_premium():
    base = item('Demonhead', "Andariel's Visage", {'0:0': 30, '60:0': 10})
    assert assess_tier(base)['tier'] == 'med'
    assert assess_tier(replace(base, ethereal=True))['tier'] == 'high'
    assert '30 strength' in ' '.join(assess_tier(replace(base, ethereal=True))['reasons'])
    assert assess_tier(replace(base, ethereal=None))['tier'] is None


@pytest.mark.parametrize(('res', 'tier'), [(26, 'med'), (27, 'high'), (30, 'high')])
def test_mara_all_resistance_roll(res, tier):
    base = item('Amulet', "Mara's Kaleidoscope", {f'{s}:0': res for s in (39, 41, 43, 45)})
    assert assess_tier(base)['tier'] == tier
    missing = {k: v for k, v in base.stats.items() if k != '45:0'}
    assert assess_tier(replace(base, stats=missing))['tier'] is None


@pytest.mark.parametrize(('pierce', 'skills', 'tier'), [(49, 2, 'med'), (50, 1, 'med'), (50, 2, 'high')])
def test_deaths_web_needs_both_poison_rolls(pierce, skills, tier):
    base = item('Unearthed Wand', "Death's Web", {'336:0': pierce, '188:17': skills})
    assert assess_tier(base)['tier'] == tier
    assert assess_tier(replace(base, stats={'336:0': {'status': 'decoded', 'value': 50}}))['tier'] is None


def test_crown_socket_count_and_perfect_combination_are_preserved():
    stats = {f'{s}:0': 30 for s in (39, 41, 43, 45)} | {'36:0': 15}
    base = item('Corona', 'Crown of Ages', stats, sockets=1)
    assert assess_tier(base)['tier'] == 'med'
    perfect = assess_tier(replace(base, sockets=2))
    assert perfect['tier'] == 'high'
    assert '2 sockets' in ' '.join(perfect['reasons'])
    assert assess_tier(replace(base, sockets=None))['tier'] is None
    assert assess_tier(replace(base, sockets=3))['tier'] is None


def test_griffon_keeps_perfect_roll_reason_and_rejects_socket_augmented_totals():
    base = item('Diadem', "Griffon's Eye", {'334:0': 20, '330:0': 15})
    result = assess_tier(base)
    assert result['tier'] == 'high'
    assert 'Perfect' in ' '.join(result['reasons'])
    assert assess_tier(replace(base, socket_contents='filled', sockets=1))['tier'] is None
    assert assess_tier(replace(base, ethereal=True))['tier'] is None
