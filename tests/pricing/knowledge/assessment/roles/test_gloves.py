from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def gloves(quality, values):
    return replace(
        facts('Chain Gloves', quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    )


def roles(item, context=None):
    return {r['id']: r for r in assess_roles(item, build()['profiles'], context)}


def test_javelin_magic_and_rare_gloves_have_distinct_profiles():
    magic = roles(gloves('magic', {'188:2': 3, '93:0': 20}))
    assert magic['lightning-fury-standard-gloves']['status'] == 'partial'
    assert 'lightning-fury-mf-gloves' not in magic
    rare = roles(gloves('rare', {'188:2': 2, '93:0': 20}))
    assert rare['lightning-fury-mf-gloves']['status'] == 'partial'
    assert rare['lightning-fury-ubers-gloves']['status'] == 'partial'
    assert rare['lightning-strike-standard-gloves']['status'] == 'partial'
    assert 'lightning-fury-standard-gloves' not in rare
    wrong = roles(gloves('rare', {'188:0': 2, '93:0': 20}))
    assert wrong['lightning-fury-mf-gloves']['status'] == 'failed'


def test_boss_glove_swap_retains_arachnid_dependency():
    item = gloves('magic', {'188:2': 3, '93:0': 20})
    assert roles(item)['lightning-strike-boss-gloves']['dependencies'][0]['status'] == 'unknown'
    assert (
        roles(item, {'player_items': ['Arachnid Mesh']})['lightning-strike-boss-gloves']['dependencies'][0]['status']
        == 'true'
    )


def test_crafted_knockback_and_crushing_blow_gloves_are_different_mechanisms():
    hit_power = roles(gloves('crafted', {'93:0': 20, '81:0': 1}))
    assert hit_power['double-throw-standard-gloves']['status'] == 'partial'
    assert hit_power['smite-high-investment-gloves']['status'] == 'failed'
    blood = roles(gloves('crafted', {'93:0': 20, '136:0': 7, '60:0': 2, '188:50': 2}))
    assert blood['smite-high-investment-gloves']['status'] == 'partial'
    assert blood['dragon-talon-budget-gloves']['status'] == 'partial'
    assert blood['double-throw-standard-gloves']['status'] == 'failed'
    assert any(p['status'] == 'false' for p in blood['smite-high-investment-gloves']['preferences'])
