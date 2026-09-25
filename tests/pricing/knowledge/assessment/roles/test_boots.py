from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def boots(values, **changes):
    return replace(
        facts('Heavy Boots', 'rare'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
    )


def roles(item):
    return {r['id']: r for r in assess_roles(item, build()['profiles'])}


def test_tri_resistance_boot_candidates_keep_subperfect_rolls_and_separate_gold_find():
    result = roles(boots({'96:0': 20, '39:0': 25, '41:0': 30, '43:0': 35}))
    for key in (
        'blizzard-standard-boots',
        'lightning-sentry-standard-boots',
        'fire-warlock-standard-boots',
        'fire-warlock-mf-boots',
        'lightning-fury-ubers-boots',
        'lightning-strike-ubers-boots',
        'fissure-ubers-boots',
        'lightning-sorceress-ubers-boots',
    ):
        assert result[key]['status'] == 'partial'
        assert any(p['status'] == 'false' for p in result[key]['preferences'])
    assert result['gold-find-budget-boots']['status'] == 'failed'
    assert not roles(boots({'96:0': 30}, rarity='unique'))


def test_gold_find_and_starter_boots_use_their_own_stat_combination():
    result = roles(boots({'96:0': 20, '39:0': 35, '79:0': 70, '99:0': 10}))
    assert result['gold-find-budget-boots']['status'] == 'partial'
    assert all(p['status'] == 'true' for p in result['gold-find-budget-boots']['preferences'])
    assert result['nova-starter-boots']['status'] == 'partial'
    assert result['blizzard-standard-boots']['status'] == 'failed'


def test_unknown_boot_resistances_never_confirm_tri_resistance_candidate():
    result = roles(boots({'96:0': 30, '39:0': 40}, capture_complete=False))
    assert result['blizzard-standard-boots']['rule_trace']['truth'] == 'unknown'
    assert result['blizzard-standard-boots']['status'] == 'partial'
