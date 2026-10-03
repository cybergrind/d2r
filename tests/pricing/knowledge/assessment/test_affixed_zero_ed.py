import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.maintenance.replay import decode_snapshot


ROOT = Path(__file__).resolve().parents[4]


def extraction(stem):
    saved = json.loads((ROOT / f'tests/inventory_tracking/fixtures/{stem}.json').read_text())
    return decode_snapshot(saved)


@pytest.mark.parametrize('stem', ['storm_gyre', 'greater_claws', 'dire_song'])
def test_native_affixes_prove_no_percent_damage_without_inventing_captured_stats(stem):
    result = assess_result(extraction(stem), profiles=[])
    assert result.contract is not None, result.price_gaps
    assert result.contract.properties['510'] == 0
    assert not {'17:0', '18:0'} & result.facts.stats.keys()


@pytest.mark.parametrize('mutation', ['missing', 'unknown', 'duplicate', 'ineligible', 'crafted', 'unidentified'])
def test_unproven_affixes_never_default_to_zero_ed(mutation):
    item = extraction('greater_claws')
    affixes = item['source']['native_affixes']
    if mutation == 'missing':
        del item['source']['native_affixes']
    elif mutation == 'unknown':
        affixes['suffix'] = [999999]
    elif mutation == 'duplicate':
        affixes['suffix'] *= 2
    elif mutation == 'ineligible':
        affixes['prefix'] = [1236]  # Captured orb Cold Skills prefix, not eligible on this claw.
    elif mutation == 'crafted':
        item['item']['rarity'] = 'crafted'
    else:
        item['item']['identified'] = False
    result = assess_result(item, profiles=[])
    assert result.contract is None


@pytest.mark.parametrize('code', ['dmg%', 'dmg%/lvl', 'unreviewed-property'])
def test_damage_or_unknown_native_modifier_prevents_absence_proof(monkeypatch, code):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_damage

    data = deepcopy(metadata())
    data['affixes']['suffix']['167']['game_definition']['mod2code'] = code
    monkeypatch.setattr(affixed_damage, 'metadata', lambda: data)
    result = assess_result(extraction('greater_claws'), profiles=[])
    assert result.contract is None
    assert 'Weapon damage-modifier coverage is unproven.' in result.price_gaps


@pytest.mark.parametrize(
    'changes',
    [
        {'capture_complete': False},
        {'socket_contents': 'unknown'},
        {'socket_contents': 'filled'},
        {'socket_items': [{'name': 'Jewel'}]},
        {'properties': {'510': 20}},
        {'stats': {'17:0': {'value': 20, 'status': 'decoded'}}},
    ],
)
def test_partial_capture_or_socket_and_damage_conflicts_block_zero_ed(changes):
    from pricing.knowledge.assessment.mechanics.affixed_damage import affixed_without_ed

    facts = assess_result(extraction('greater_claws'), profiles=[]).facts
    assert not affixed_without_ed(replace(facts, **changes))


def test_exact_affix_comparison_does_not_default_missing_listing_ed_to_zero():
    from pricing.knowledge.assessment.comparables import reject_reasons

    contract = assess_result(extraction('greater_claws'), profiles=[]).contract.to_dict()
    row = {
        **contract,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'seller',
        'listing_id': 'listing',
        'observed_at': '2026-10-02',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract, row)
    missing = {k: v for k, v in row['properties'].items() if k != '510'}
    assert reject_reasons(contract, {**row, 'properties': missing})
    assert reject_reasons(contract, {**row, 'properties': {**missing, '510': 20}})


@pytest.mark.parametrize(
    ('prefix', 'suffix', 'expected'),
    [
        (1023, 352, True),  # Bronze / Leech: attack rating and life steal.
        (1330, 383, True),  # Ember / Strength: both fire endpoints and strength.
        (1335, 167, True),  # Static / Alacrity: lightning endpoints and attack speed.
        (1042, 352, False),  # Sharp also adds percent damage, despite its attack rating.
    ],
)
def test_selected_native_weapon_affixes_distinguish_elemental_and_percent_damage(prefix, suffix, expected):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.affixed_damage import affixed_without_ed

    facts = assess_result(extraction('greater_claws'), profiles=[]).facts
    affixes = {'prefix': [prefix], 'suffix': [suffix], 'auto': []}
    for table in ('prefix', 'suffix'):
        entry = metadata()['affixes'][table][str(affixes[table][0])]
        assert facts.base_code in entry['base_codes']
    provenance = {**facts.provenance, 'capture': {**facts.provenance['capture'], 'native_affixes': affixes}}
    candidate = replace(facts, native_affixes=affixes, provenance=provenance)
    assert affixed_without_ed(candidate) is expected


def test_reviewed_properties_still_write_only_non_ed_native_stats():
    from pricing.knowledge.assessment.mechanics.affixed_damage import NON_DAMAGE_PROPERTIES

    properties = json.loads((ROOT / 'third-parties/d2data/json/properties.json').read_text())
    damage_stats = {'item_maxdamage_percent', 'item_mindamage_percent', 'item_maxdamage_percent_perlevel'}
    for code in NON_DAMAGE_PROPERTIES:
        row = properties[code]
        effects = [i for i in range(1, 8) if row.get(f'func{i}')]
        assert effects, code
        for i in effects:
            assert row[f'func{i}'] in (1, 3, 8, 10, 19), code
            assert row.get(f'stat{i}'), code
            assert row[f'stat{i}'] not in damage_stats, code
