"""Flat damage on affixed non-weapons reaches the triage properties the jewel rules read (2026-10-22 RCA).

A captured jewel carries +max damage as native stats 22/24/160 (and +min as 21/23/159), never as a market
property. Triage once dropped them, so a 15-max level-18 Jewel of Carnage became `{'796': 18}` -> vendor and was
sold in town (rca/2026-10-22/jewel-rules-inventory.md, V1).
"""

from typing import Any

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.exact import AffixedHandler
from pricing.knowledge.assessment.mechanics import affix_effects
from pricing.triage.adapters import from_drop
from pricing.triage.engine import assess
from pricing.triage.runtime import TABLES
from tests.pricing.knowledge.assessment.item_bank.models import Item


def stat(stat_id, value, name):
    return {
        'memory_stat': {'layer': 0, 'id': stat_id, 'raw': value},
        'status': 'decoded',
        'name': name,
        'value': value,
    }


def carnage_capture(maximum=15, suffix=222):
    """The stored Alt+D capture of 2026-10-11 23:21 (runs/alt-d/20261011T231359Z-a9714874), trimmed to its facts."""
    return {
        'item': {
            'name': 'Jewel',
            'base_name': 'Jewel',
            'base_code': 'jew',
            'item_type': 'jewl',
            'identified': True,
            'category': 'misc',
            'rarity': 'magic',
            'affixes': [],
            'sockets': 0,
            'ethereal': False,
            'socket_contents': 'empty',
            'socket_items': [],
            'empty_sockets': 0,
            'filled_sockets': 0,
        },
        'source': {
            'engine': 'memory_snapshot',
            'native_affixes': {'prefix': [], 'suffix': [suffix], 'auto': []},
            'stat_capture_complete': True,
        },
        'unresolved_stats': [],
        'decoded_stats': [
            stat(22, maximum, 'maxdamage'),
            stat(24, maximum, 'secondary_maxdamage'),
            stat(160, maximum, 'item_throw_maxdamage'),
        ],
    }


def test_stored_level_18_carnage_jewel_keeps_its_maximum_damage_and_is_not_sold():
    item = from_drop(carnage_capture())
    assert item['properties'] == {'448': 15, '796': 18}
    assert assess(item, TABLES.load())['verdict'] != 'vendor'


def captured(code, rarity, raw_stats):
    row: dict[str, Any] = Item(code, rarity, raw_stats=raw_stats, complete=True).capture()
    row['item']['affixes'] = row.pop('affixes', row['item'].get('affixes', []))
    return row


@pytest.mark.parametrize(
    ('raw_stats', 'expected'),
    [
        (((22, 0, 15), (24, 0, 15), (160, 0, 15)), {'448': 15}),
        (((21, 0, 8), (23, 0, 8), (159, 0, 8)), {'416': 8}),
        (((21, 0, 3), (23, 0, 3), (159, 0, 3), (22, 0, 9), (24, 0, 9), (160, 0, 9)), {'416': 3, '448': 9}),
    ],
)
@pytest.mark.parametrize(('base', 'rarity'), [('Jewel', 'magic'), ('Jewel', 'rare'), ('Ring', 'rare')])
def test_flat_damage_mirrors_become_one_market_bonus(base, rarity, raw_stats, expected):
    properties = from_drop(captured(base, rarity, raw_stats))['properties']
    assert {key: properties.get(key) for key in expected} == expected


@pytest.mark.parametrize(
    'raw_stats',
    [((22, 0, 10), (24, 0, 14)), ((24, 0, 10),)],
    ids=['conflicting mirrors', 'secondary without primary'],
)
def test_undecidable_flat_damage_is_left_out_not_guessed(raw_stats):
    assert '448' not in from_drop(captured('Jewel', 'magic', raw_stats))['properties']


def test_weapon_damage_totals_are_not_flat_bonuses():
    properties = from_drop(captured('Phase Blade', 'magic', ((21, 0, 31), (22, 0, 35))))['properties']
    assert '416' not in properties
    assert '448' not in properties


def test_triage_and_detail_engine_read_affix_effects_through_one_projection(monkeypatch):
    """Guard: a projector added to the shared list reaches both paths, so their mappings cannot drift."""

    def marker(facts):
        return {'99999': 7}, set(), []

    monkeypatch.setattr(affix_effects, 'PROJECTORS', (*affix_effects.PROJECTORS, marker))
    row = carnage_capture()
    contract, _ = AffixedHandler().contract(normalize(row), 'jewel')
    assert contract is not None
    assert contract.properties['99999'] == 7
    assert contract.properties['448'] == 15
    assert from_drop(row)['properties']['99999'] == 7


def test_every_shared_effect_property_reaches_triage():
    row = captured('Jewel', 'rare', ((21, 0, 8), (23, 0, 8), (159, 0, 8), (22, 0, 9), (24, 0, 9), (160, 0, 9)))
    shared, _, _ = affix_effects.affix_effect_properties(normalize(row))
    assert shared == {'416': 8, '448': 9}
    assert shared.items() <= from_drop(row)['properties'].items()
