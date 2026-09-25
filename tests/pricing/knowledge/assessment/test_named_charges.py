from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def puzzler(remaining=42, maximum=69, level=11):
    key = f'204:{54 * 64 + level}'
    item = facts('Elder Staff', 'set', "Naj's Puzzler")
    stats = {
        f'{stat}:0': {'id': stat, 'status': 'decoded', 'value': value, 'raw': value}
        for stat, value in ((50, 6), (51, 45))
    }
    from pricing.knowledge.assessment.handlers.definitions import named_definitions

    for spec in named_definitions()['set', "Naj's Puzzler"]['roll_ranges'].values():
        stats[f'{spec["stat_id"]}:0'] = {
            'id': spec['stat_id'],
            'status': 'decoded',
            'value': spec['min'],
            'raw': spec['min'],
        }
    stats[key] = {
        'id': 204,
        'parameter': 54 * 64 + level,
        'status': 'decoded',
        'unit': 'charges_remaining',
        'value': remaining,
        'raw': maximum * 256 + remaining,
        'charges': {'remaining': remaining, 'maximum': maximum},
    }
    return replace(
        item,
        stats=stats,
        properties={'478': 6, '479': 45},
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )


def test_named_teleport_charge_level_is_intrinsic_and_not_remaining_uses():
    item = puzzler()
    contract, gaps = HANDLERS['named'].contract(item, 'weapon')
    assert contract is not None, gaps
    assert contract.properties['526'] == 11
    assert contract.intrinsic_properties['526'] == 11
    assert item.stats['204:3467']['value'] == 42
    # Rechargeable use depletion is not a different skill-level roll.
    empty, gaps = HANDLERS['named'].contract(puzzler(remaining=0), 'weapon')
    assert empty is not None, gaps
    assert empty.properties == contract.properties


@pytest.mark.parametrize('change', ['missing', 'capacity', 'level', 'raw', 'unit', 'ethereal'])
def test_unverified_named_charge_state_blocks_comparison(change):
    item = puzzler(maximum=68 if change == 'capacity' else 69, level=10 if change == 'level' else 11)
    if change == 'missing':
        item = replace(
            item, stats={k: v for k, v in item.stats.items() if not k.startswith('204:')}, projection_gaps=[]
        )
    elif change in ('raw', 'unit'):
        stats = {k: dict(v) for k, v in item.stats.items()}
        stats['204:3467'][change] = 0 if change == 'raw' else 'unknown'
        item = replace(item, stats=stats)
    elif change == 'ethereal':
        item = replace(item, ethereal=True)
    contract, gaps = HANDLERS['named'].contract(item, 'weapon')
    assert contract is None
    assert any('charge' in gap.lower() for gap in gaps)


def test_named_charge_comparisons_accept_fixed_omission_but_reject_wrong_skill_level():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons

    contract, gaps = HANDLERS['named'].contract(puzzler(), 'weapon')
    assert contract is not None, gaps
    contract = contract.to_dict()
    required = {k: v for k, v in contract['properties'].items() if k not in contract['intrinsic_properties']}
    rows = [
        {
            **contract,
            'properties': required,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 1,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, '526': 42}})
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, '719': 11}})


def test_charge_field_labels_and_named_skill_aliases_match_cached_primary_data():
    import json
    from pathlib import Path

    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.handlers.definitions import named_definitions
    from pricing.knowledge.assessment.mechanics.named_charges import MARKET_FIELDS

    root = Path(__file__).resolve().parents[4]
    fields = json.loads((root / 'pricing/data/appraisal-properties.json').read_text())['properties']
    skills = metadata()['skills']
    for skill, prop in MARKET_FIELDS.items():
        name = skills[str(skill)]['name']
        assert f'Level {{{{value}}}} {name} ({{{{charges}}}}/{{{{charges}}}} Charges)' in fields[prop]['labels']
    native = json.loads((root / 'third-parties/d2data/json/skills.json').read_text())
    native_ids = {row['skill'].casefold(): row['*Id'] for row in native.values() if 'skill' in row and '*Id' in row}
    for definition in named_definitions().values():
        record = definition['game_definition']
        for slot in range(1, 13):
            if record.get(f'prop{slot}') != 'charged':
                continue
            name = record[f'par{slot}']
            if not isinstance(name, str):
                continue
            matches = [
                int(key)
                for key, row in skills.items()
                if row.get('internal_name', row['name']).replace(' ', '').casefold() == name.replace(' ', '').casefold()
            ]
            assert matches == [native_ids[name.casefold()]], name


@pytest.mark.parametrize(
    ('name', 'base', 'skill', 'level', 'capacity'),
    [
        ('Wolfhowl', 'Fury Visor', 237, 15, 18),
        ('Carrion Wind', 'Ring', 222, 21, 15),
    ],
)
def test_localized_named_charges_resolve_original_game_definition(name, base, skill, level, capacity):
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.definitions import named_definitions
    from pricing.knowledge.assessment.mechanics.named_charges import fixed_charge_properties

    raw = {'id': 204, 'layer': skill * 64 + level, 'raw': (capacity << 8) + capacity}
    decoded, _, unresolved = decode_stats([raw])
    assert not unresolved
    item = normalize({'item': facts(base, 'unique', name).to_dict(), 'decoded_stats': decoded})
    _, consumed, gaps = fixed_charge_properties(item, named_definitions()['unique', name])
    assert not gaps
    assert consumed == {f'204:{raw["layer"]}'}
