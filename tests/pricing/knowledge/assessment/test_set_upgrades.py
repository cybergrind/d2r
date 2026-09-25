from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.definitions import named_definitions, resolve_named_definition
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def captured(base, name):
    definition = named_definitions()['set', name]
    return replace(
        facts(base, 'set', name),
        provenance={'capture': {'item_identity': {'table': 'set', 'table_id': definition['table_id']}}},
    )


@pytest.mark.parametrize(
    ('name', 'base'),
    [
        ("Sazabi's Mental Sheath", 'Giant Conch'),
        ("Tancred's Crowbill", 'Crowbill'),
        ("Tancred's Crowbill", 'War Spike'),
    ],
)
def test_verified_set_upgrade_resolves_original_definition(name, base):
    item = captured(base, name)
    definition, gaps = resolve_named_definition(item)
    assert not gaps
    assert definition == named_definitions()['set', name]
    assert resolve_named_definition(replace(item, provenance={}))[0] is None
    for identity in ({'table': 'unique', 'table_id': definition['table_id']}, {'table': 'set', 'table_id': -1}):
        assert resolve_named_definition(replace(item, provenance={'capture': {'item_identity': identity}}))[0] is None


@pytest.mark.parametrize('base', ['Full Helm', 'Diadem'])
def test_set_upgrade_rejects_downgrade_and_unrelated_base(base):
    assert resolve_named_definition(captured(base, "Sazabi's Mental Sheath"))[0] is None


def market_row(tier, defense=260):
    values = {
        '799': 'softcore',
        '800': False,
        '798': 'PC',
        '1854': 'reign of the warlock',
        '738': False,
        '402': 0,
        '934': '',
        '930': tier,
        '1216': tier == 'Elite',
        '1855': defense,
        '427': 19,
        '428': 20,
        '587': 1,
    }
    raw = {
        'id': f'set-upgrade-{tier}-{defense}',
        'seller_id': 'seller',
        'amount': 1,
        'active': True,
        'selling': True,
        'completed': False,
        'prices': [{'name': 'Ist Rune', 'quantity': 1}],
        'properties': [
            {'property_id': key, 'type': kind, kind: value}
            for key, value in values.items()
            for kind in ['bool' if type(value) is bool else 'number' if type(value) is int else 'string']
        ],
    }
    return normalize_listing(
        raw,
        name="Sazabi's Mental Sheath",
        category='sets',
        source='fixture',
        observed_at='2026-09-24',
        currencies={'ist': 1},
    )


def test_upgraded_set_prices_match_actual_base_defense_and_nonethereal_state():
    item = replace(
        captured('Giant Conch', "Sazabi's Mental Sheath"),
        stats={f'{s}:0': {'status': 'decoded', 'value': v} for s, v in [(31, 260), (127, 1), (39, 19), (41, 20)]},
        properties={'587': 1, '427': 19, '428': 20},
    )
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.base_code == item.base_code
    matching = market_row('Elite')
    wrong_base = market_row('Exceptional')
    wrong_defense = market_row('Elite', 259)
    result = evaluate(contract.to_dict(), [matching, wrong_base, wrong_defense])
    assert result['accepted'] == [matching], result['rejected']
    assert len(result['rejected']) == 2
    assert NamedHandler().contract(replace(item, ethereal=True), 'helm')[0] is None
