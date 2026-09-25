from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler, definitions
from pricing.knowledge.runewords import build


ROOT = Path(__file__).resolve().parents[4]


def test_runeword_census_preserves_definitions_ranges_and_demand():
    report = build(ROOT)
    spirit = next(r['details'] for r in report['rows'] if r['name'] == 'Spirit')
    assert spirit['variable_stats']['105']['min'] == 25
    assert spirit['variable_stats']['105']['max'] == 35
    assert spirit['demand']
    assert report['coverage']['definitions'] == len(definitions())


def test_runeword_contract_requires_base_and_all_variable_rolls():
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Monarch')
    facts = ItemFacts(
        'Spirit', 'Monarch', base['code'], base['type'], 'normal', 'Spirit', True, False, 4, 'filled', [], True
    )
    handler = RunewordHandler()
    contract, gaps = handler.contract(facts, 'shield')
    assert contract is None
    assert any('105' in g for g in gaps)
    assert any('defense' in g for g in gaps)
    facts = replace(
        facts,
        stats={
            f'{stat}:0': {'id': stat, 'value': value, 'status': 'decoded'}
            for stat, value in [(105, 35), (9, 112), (147, 8), (31, 148)]
        },
    )
    contract, gaps = handler.contract(facts, 'shield')
    assert not gaps
    assert contract.base_code == base['code']
    assert contract.properties['1855'] == 148
    row = {
        'name': 'Spirit',
        'rarity': 'runeword',
        'base_rarity': 'normal',
        'ethereal': False,
        'sockets': 4,
        'socket_contents': 'filled',
        'scope_status': 'verified',
        'properties': contract.to_dict()['properties'],
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'seller',
        'ask_ist': 1,
        'base_code': base['code'],
    }
    assert not reject_reasons(contract.to_dict(), row)
    wrong = deepcopy(row)
    wrong.pop('base_code')
    assert 'Different or unknown runeword base.' in reject_reasons(contract.to_dict(), wrong)
    facts = replace(facts, projection_gaps=[*facts.projection_gaps, 'Unmapped magic absorb roll'])
    assert handler.contract(facts, 'shield')[0] is None


def test_market_runeword_base_selector_does_not_invent_ethereal_flag():
    from pricing.knowledge.market import normalize_listing

    raw = {
        'id': 'test',
        'amount': 1,
        'properties': [
            {'property_id': 1197, 'property': 'Base Item (Shield, Sword) 4', 'type': 'string', 'string': 'Monarch'}
        ],
    }
    row = normalize_listing(raw, name='Spirit', category='runewords', source='test', currencies={})
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Monarch')
    assert row['base_code'] == base['code']
    assert row['sockets'] == 4
    assert row['socket_contents'] == 'filled'
    assert row['rarity'] == 'runeword'
    assert 'ethereal' not in row
    raw['properties'][0]['string'] = 'No base'
    row = normalize_listing(raw, name='Spirit', category='runewords', source='test', currencies={})
    assert 'base_code' not in row
    assert row['socket_contents'] == 'unknown'


def test_call_to_arms_requires_each_distinct_warcry_roll():
    from tests.pricing.knowledge.assessment.test_family_contracts import facts as base_facts

    item = replace(
        base_facts('Crystal Sword'),
        name='Call to Arms',
        runeword='Call to Arms',
        sockets=5,
        socket_contents='filled',
        stats={
            '17:0': {'id': 17, 'value': 270, 'status': 'decoded'},
            '18:0': {'id': 18, 'value': 270, 'status': 'decoded'},
            '97:155': {'id': 97, 'value': 6, 'status': 'decoded'},
        },
    )
    handler = RunewordHandler()
    contract, gaps = handler.contract(item, 'weapon')
    assert contract is None
    assert any('97:149' in gap for gap in gaps)
    assert any('97:146' in gap for gap in gaps)
    complete = {
        **item.stats,
        '97:149': {'id': 97, 'value': 6, 'status': 'decoded'},
        '97:146': {'id': 97, 'value': 4, 'status': 'decoded'},
    }
    assert handler.contract(replace(item, stats=complete), 'weapon')[0] is not None
    for invalid in (None, True, float('nan'), float('inf')):
        broken = {**complete, '97:149': {'id': 97, 'value': invalid, 'status': 'decoded'}}
        assert handler.contract(replace(item, stats=broken), 'weapon')[0] is None
    unresolved = {**complete, '97:149': {'id': 97, 'value': 6, 'status': 'unresolved'}}
    assert handler.contract(replace(item, stats=unresolved), 'weapon')[0] is None
