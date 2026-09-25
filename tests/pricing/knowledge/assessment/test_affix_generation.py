"""Unavailable affixes must neither establish nor obscure a comparison."""

from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.mechanics import affixed_charges, affixed_per_level, affixed_triggers
from tests.pricing.knowledge.assessment.test_affixed_charges import orb
from tests.pricing.knowledge.assessment.test_affixed_per_level import weapon as scaling_weapon
from tests.pricing.knowledge.assessment.test_affixed_triggers import weapon as proc_weapon


@pytest.mark.parametrize('frequency', [0, None])
@pytest.mark.parametrize(
    ('module', 'make_item'),
    [(affixed_charges, orb), (affixed_triggers, proc_weapon), (affixed_per_level, scaling_weapon)],
)
def test_non_generating_affixes_cannot_establish_a_price_contract(monkeypatch, module, make_item, frequency):
    data = deepcopy(metadata())
    for table in data['affixes'].values():
        for row in table.values():
            if frequency is None:
                row['game_definition'].pop('frequency', None)
            else:
                row['game_definition']['frequency'] = frequency
    monkeypatch.setattr(module, 'metadata', lambda: data)
    monkeypatch.setattr(module, 'metadata_generation', lambda: f'disabled-{module.__name__}-{frequency}')
    assert HANDLERS['affixed'].contract(make_item(), 'weapon')[0] is None


@pytest.mark.parametrize('kind', ['charge', 'proc'])
def test_obsolete_alternate_does_not_create_false_ambiguity(monkeypatch, kind):
    data = deepcopy(metadata())
    module, make_item = (affixed_charges, orb) if kind == 'charge' else (affixed_triggers, proc_weapon)
    name = 'of Novas' if kind == 'charge' else 'of Damage Amplification'
    entry = next(
        e for e in data['affixes']['suffix'].values() if e['name'] == name and make_item().base_code in e['base_codes']
    )
    extra = deepcopy(entry)
    extra['game_definition']['frequency'] = 0
    if kind == 'charge':
        extra['game_definition']['mod1min'] = 20
    else:
        extra['game_definition']['mod1max'] = 2
    data['affixes']['suffix']['obsolete-test'] = extra
    monkeypatch.setattr(module, 'metadata', lambda: data)
    monkeypatch.setattr(module, 'metadata_generation', lambda: f'obsolete-alternate-{kind}')
    contract, gaps = HANDLERS['affixed'].contract(make_item(), 'weapon')
    assert contract is not None, gaps
