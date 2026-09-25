from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def weapon(stat=198, skill=66, level=1, chance=5, rarity='rare', base='Long Sword'):
    parameter = skill * 64 + level
    key = f'{stat}:{parameter}'
    return replace(
        facts(base, rarity),
        properties={'510': 0},
        stats={
            **{f'{s}:0': {'status': 'decoded', 'value': 0} for s in (17, 18)},
            key: {
                'parameter': parameter,
                'status': 'decoded',
                'unit': 'percent_chance',
                'raw': chance,
                'value': chance,
            },
        },
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )


@pytest.mark.parametrize('rarity', ['magic', 'rare'])
def test_amplify_damage_affix_supports_exact_chance_comparison(rarity):
    contract, gaps = HANDLERS['affixed'].contract(weapon(rarity=rarity), 'weapon')
    assert contract is not None, gaps
    assert contract.properties == {'510': 0, '543': 5}
    assert '543' not in contract.intrinsic_properties
    payload = contract.to_dict()
    rows = [
        {
            **payload,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 2,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 2
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0}})
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0, '543': 1}})


def test_nova_wand_projects_chance_not_skill_level():
    contract, gaps = HANDLERS['affixed'].contract(
        weapon(skill=48, level=3, chance=10, rarity='magic', base='Bone Wand'), 'weapon'
    )
    assert contract is not None, gaps
    assert contract.properties['542'] == 10


@pytest.mark.parametrize(
    'item',
    [
        weapon(level=2),
        weapon(chance=6),
        weapon(stat=195),
        weapon(rarity='crafted'),
        weapon(stat=195, skill=53, level=3, chance=8),
        weapon(stat=195, skill=53, level=5, chance=8),
    ],
)
def test_invalid_or_ambiguous_proc_levels_do_not_share_a_scalar_price(item):
    assert HANDLERS['affixed'].contract(item, 'weapon')[0] is None


def test_corrupt_proc_payload_is_rejected_even_without_adapter_gap():
    item = weapon()
    key = '198:4225'
    for change in ({'raw': 1}, {'unit': 'unverified'}, {'parameter': 4226}, {'value': True}):
        changed = replace(item, projection_gaps=[], stats={**item.stats, key: {**item.stats[key], **change}})
        assert HANDLERS['affixed'].contract(changed, 'weapon')[0] is None


def test_separate_affix_groups_cannot_hide_summed_proc_ambiguity(monkeypatch):
    import copy

    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_triggers

    data = copy.deepcopy(metadata())
    entry = next(e for e in data['affixes']['suffix'].values() if e['name'] == 'of Damage Amplification')
    extra = copy.deepcopy(entry)
    extra['game_definition']['group'] += 1
    data['affixes']['suffix']['extra-trigger-group'] = extra
    monkeypatch.setattr(affixed_triggers, 'metadata', lambda: data)
    monkeypatch.setattr(affixed_triggers, 'metadata_generation', lambda: 'two-trigger-groups')
    assert HANDLERS['affixed'].contract(weapon(), 'weapon')[0] is None


def test_crafted_weapon_random_proc_requires_verified_recipe_base():
    contract, gaps = HANDLERS['affixed'].contract(weapon(rarity='crafted', base='Axe'), 'weapon')
    assert contract is not None, gaps
    assert contract.properties['543'] == 5
    assert HANDLERS['affixed'].contract(weapon(rarity='crafted', base='Long Sword'), 'weapon')[0] is None


def crafted_frost(base):
    parameter = 44 * 64 + 4
    return replace(
        facts(base, 'crafted'),
        properties={'418': 4},
        stats={
            f'201:{parameter}': {
                'parameter': parameter,
                'status': 'decoded',
                'unit': 'percent_chance',
                'raw': 5,
                'value': 5,
            }
        },
        projection_gaps=[f'No verified market mapping for native stat 201:{parameter}.'],
    )


def test_crafted_ring_recipe_proc_is_unique_but_amulet_shares_chance_with_another_level():
    contract, gaps = HANDLERS['affixed'].contract(crafted_frost('Ring'), 'jewelry')
    assert contract is not None, gaps
    assert contract.properties['434'] == 5
    assert '434' not in contract.intrinsic_properties
    # The same 5% field also describes the level-3 Frost Shield affix on amulets.
    assert HANDLERS['affixed'].contract(crafted_frost('Amulet'), 'jewelry')[0] is None
