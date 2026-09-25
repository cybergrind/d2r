from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.test_family_contracts import facts, scalar_properties


def charm(name, base, changes=None):
    definition = catalog().named['unique', name]
    values = {f'{s["stat_id"]}:{s.get("layer", 0)}': s['min'] for s in definition['roll_ranges'].values()}
    values.update(changes or {})
    stats = {key: {'status': 'decoded', 'value': value} for key, value in values.items()}
    return replace(facts(base, 'unique', name), stats=stats, properties=scalar_properties(stats))


@pytest.mark.parametrize(
    ('name', 'base', 'changes'),
    [
        ('Annihilus', 'Small Charm', {'0:0': 21}),
        ('Annihilus', 'Small Charm', {'85:0': 11}),
        ("Gheed's Fortune", 'Grand Charm', {'87:0': 16}),
        ('Flame Rift', 'Grand Charm', {'39:0': -69}),
        ('Black Cleft', 'Grand Charm', {'37:0': -66}),
        ('Flame Rift', 'Grand Charm', {'189:0': 1}),
    ],
)
def test_named_charm_contract_rejects_impossible_standalone_rolls(name, base, changes):
    contract, gaps = NamedHandler().contract(charm(name, base, changes), 'charm')
    assert contract is None
    assert any('range' in gap for gap in gaps)


@pytest.mark.parametrize(('name', 'base'), [('Annihilus', 'Small Charm'), ('Hellfire Torch', 'Large Charm')])
@pytest.mark.parametrize('changed', ['0:0', '39:0'])
def test_all_attributes_and_resistances_are_one_roll_each(name, base, changed):
    item = charm(name, base, {changed: 11})
    gaps = roll_gaps(item, catalog().named['unique', name])
    assert any('shared roll' in gap for gap in gaps)


@pytest.mark.parametrize('value', [10, 15, 20])
def test_annihilus_legal_shared_rolls_form_a_contract(value):
    changes = {f'{stat}:0': value for stat in (0, 1, 2, 3, 39, 41, 43, 45)}
    contract, gaps = NamedHandler().contract(charm('Annihilus', 'Small Charm', changes), 'charm')
    assert contract is not None, gaps


def test_separately_rolled_resistances_are_not_forced_equal():
    # Sazabi's fire/lightning bonuses are separate rolls, unlike res-all.
    definition = catalog().named['set', "Sazabi's Mental Sheath"]
    item = replace(
        facts('Basinet', 'set', "Sazabi's Mental Sheath"),
        stats={
            f'{s["stat_id"]}:0': {'status': 'decoded', 'value': 19 if s['stat_id'] == 39 else s['min']}
            for s in definition['roll_ranges'].values()
        },
    )
    assert not roll_gaps(item, definition)
