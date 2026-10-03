"""Item-level-derived proc levels remain explicit comparison dimensions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.variable_triggers import listing_level_gaps, variable_trigger_properties


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_variable_triggers.json').read_text())['records']


@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value', 'level', 'skill', 'unit', 'unknown'])
def test_stormspire_observed_variable_level_requires_native_chance_and_skill(mutation):
    observation = deepcopy(next(r['observation'] for r in RECORDS if r['name'] == 'Stormspire'))
    row = next(r for r in observation['decoded_stats'] if r.get('memory_stat', {}).get('layer') == 2452)
    observation['item']['item_level'] = 90
    if mutation == 'missing':
        observation['decoded_stats'].remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 1
    elif mutation == 'level':
        row['memory_stat']['layer'] -= 1
    elif mutation == 'skill':
        row['memory_stat']['layer'] += 64
    elif mutation == 'unit':
        row['unit'] = 'points'
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    definition, gaps = resolve_named_definition(facts)
    assert not gaps
    props, levels, consumed, gaps = variable_trigger_properties(facts, definition)
    if mutation == 'unchanged':
        assert (props, levels, consumed, gaps) == ({'433': 2}, {'433': 20}, {'201:2452'}, [])
    else:
        assert gaps
        assert not consumed


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
def test_missing_item_level_preserves_observed_level_but_never_invents_market_fields(record):
    facts = normalize(record['observation'])
    assert facts.item_level is None
    definition, _ = resolve_named_definition(facts)
    props, levels, consumed, gaps = variable_trigger_properties(facts, definition)
    if record['name'] == 'Stormspire':
        assert levels == {'433': 20}
        assert not gaps
    else:
        assert not props
        assert not levels
        assert not consumed
        assert any('market' in g for g in gaps)


@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'level', 'chance', 'label', 'duplicate', 'bool'])
def test_listing_requires_exact_proc_level_and_chance(mutation):
    row = {
        'property_id': 433,
        'type': 'number',
        'number': 2,
        'property': '{{value}}% Chance to cast level {{level}} Charged Bolt when struck',
        'format': {'template': {'level': 20}},
    }
    listing = {'properties': {'433': 2}, 'raw_properties': [row]}
    if mutation == 'missing':
        listing['raw_properties'] = []
    elif mutation == 'level':
        row['format']['template']['level'] = 19
    elif mutation == 'chance':
        row['number'] = 3
    elif mutation == 'label':
        row['property'] = '{{value}}% Chance to cast level {{level}} Charged Bolt on striking'
    elif mutation == 'duplicate':
        listing['raw_properties'].append(deepcopy(row))
    elif mutation == 'bool':
        row['format']['template']['level'] = True
    gaps = listing_level_gaps({'433': 20}, {'433': 2}, listing)
    assert bool(gaps) is (mutation != 'unchanged')


def test_stormspire_comparison_requires_level_even_with_exact_chance():
    from pricing.knowledge.assessment.comparables import reject_reasons
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from pricing.knowledge.assessment.registry import classify

    observation = next(r['observation'] for r in RECORDS if r['name'] == 'Stormspire')
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is not None, gaps
    contract = contract.to_dict()
    assert contract['trigger_levels'] == {'433': 20}
    assert contract['properties']['433'] == 2
    listing = {
        **{k: contract[k] for k in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents')},
        'properties': dict(contract['properties']),
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'test-seller',
        'ask_ist': 1,
        'raw_properties': [
            {
                'property_id': 433,
                'type': 'number',
                'number': 2,
                'property': '{{value}}% Chance to cast level {{level}} Charged Bolt when struck',
                'format': {'template': {'level': 20}},
            }
        ],
    }
    assert reject_reasons(contract, listing) == []
    for level in (None, 19, True):
        changed = deepcopy(listing)
        changed['raw_properties'][0]['format']['template']['level'] = level
        assert any('level' in g.lower() for g in reject_reasons(contract, changed))
    assert any('level' in g.lower() for g in reject_reasons(contract, {**listing, 'raw_properties': []}))


@pytest.mark.parametrize(('ilvl', 'expected'), [(1, 1), (4, 1), (5, 2), (76, 19), (77, 20), (99, 20)])
def test_charged_bolt_level_clamps_at_native_boundary(ilvl, expected):
    from pricing.knowledge.assessment.mechanics.variable_triggers import proc_level

    assert proc_level(ilvl, 1, 20, 0) == expected


@pytest.mark.parametrize('format_value', [None, [], {'template': None}, {'template': []}])
def test_malformed_listing_template_is_rejected_without_crashing(format_value):
    row = {
        'property_id': 433,
        'type': 'number',
        'number': 2,
        'property': '{{value}}% Chance to cast level {{level}} Charged Bolt when struck',
        'format': format_value,
    }
    assert listing_level_gaps({'433': 20}, {'433': 2}, {'properties': {'433': 2}, 'raw_properties': [row]})
