"""Recipe material imports preserve exact identity, modifiers, quantity and scope."""

from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.assessment.policies.quest_materials import TRADEABLE, definitions
from tests.pricing.knowledge.assessment.item_bank.models import Item
from tests.pricing.knowledge.test_market_consumables import imported


@pytest.mark.parametrize('code', sorted(TRADEABLE))
def test_every_reviewed_material_can_match_three_exact_single_item_asks(code):
    native = definitions()[code]
    contract = assess(Item(native['name'], 'normal', complete=True).capture(), profiles=[])['contract']
    assert contract['name'] == native['market_name']
    rows = [imported(native['market_name'], str(i)) for i in range(3)]
    assert all(row.get('base_code') == code for row in rows)
    compared = evaluate(contract, rows)
    assert len(compared['accepted']) == 3
    assert price_from_comparables(compared, today=date(2026, 9, 28))['estimate_ist'] == 1  # Synthetic only.


@pytest.mark.parametrize('amount', [None, True, -1, 0, 2, 3])
def test_single_material_contract_never_prices_a_lot_even_with_a_false_unit_label(amount):
    contract = assess(Item('Key of Terror', 'normal', complete=True).capture(), profiles=[])['contract']
    row = imported('Key of Terror', 'bad', amount=amount)
    row['unit_policy'] = 'single_item'
    assert not evaluate(contract, [row])['accepted']


@pytest.mark.parametrize(
    'extra',
    [
        [('800', 'bool', True)],
        [('799', 'string', 'hardcore')],
        [('797', 'string', 'magic')],
        [('738', 'bool', True)],
        [('402', 'number', 1)],
        [('934', 'string', 'Ber Rune')],
        [('441', 'number', 20)],
    ],
)
def test_conflicting_scope_facets_and_modifiers_remain_rejected(extra):
    contract = assess(Item('Key of Terror', 'normal', complete=True).capture(), profiles=[])['contract']
    assert not evaluate(contract, [imported('Key of Terror', 'bad', extra=extra)])['accepted']


@pytest.mark.parametrize('name', ['3x3 Key Set', 'Statue Set', 'Shard Set', 'Horadric Cube', 'Standard of Heroes'])
def test_sets_and_quest_only_catalogs_do_not_inherit_material_facts(name):
    row = imported(name, 'fixture')
    assert row.get('facet_basis', {}).get('base_code', {}).get('kind') != 'native_recipe_material'


def test_review_queries_localized_catalog_but_retains_native_identity():
    from pricing.knowledge.assessment.maintenance.quest_material_market_review import REVIEW

    rows = [imported('Charged Essence of Hatred', str(i)) for i in range(3)]
    records = REVIEW.audit(rows, date(2026, 9, 28))
    record = next(r for r in records if r['base_code'] == 'ceh')
    assert record['name'] == 'Charged Essense of Hatred'
    assert record['cached_observations'] == 3
    assert record['price']['estimate_ist'] == 1  # Synthetic asks only.
