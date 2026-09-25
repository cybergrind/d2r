from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_azurewrath_selects_legacy_or_current_definition_by_base():
    legacy, gaps = resolve_named_definition(facts('Crystal Sword', 'unique', 'Azurewrath'))
    current, current_gaps = resolve_named_definition(facts('Phase Blade', 'unique', 'Azurewrath'))
    assert not gaps
    assert not current_gaps
    assert legacy['table_id'] == 29
    assert current['table_id'] == 301


@pytest.mark.parametrize('table_id', range(392, 400))
def test_facet_definition_uses_captured_table_id_not_last_named_record(table_id):
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': table_id}}},
    )
    definition, gaps = resolve_named_definition(item)
    assert not gaps
    assert definition['table_id'] == table_id


def test_ambiguous_missing_or_conflicting_facet_identity_never_guesses_variant():
    item = facts('Jewel', 'unique', 'Rainbow Facet')
    assert resolve_named_definition(item)[0] is None
    for identity in (
        {'table': 'unique', 'table_id': 29},
        {'table': 'set', 'table_id': 392},
        {'table': 'unique', 'table_id': True},
    ):
        assert resolve_named_definition(replace(item, provenance={'capture': {'item_identity': identity}}))[0] is None


def test_named_comparison_cannot_default_an_unidentified_facet_variant_to_poison():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        stats={
            '336:0': {'status': 'decoded', 'value': 5},
            '332:0': {'status': 'decoded', 'value': 5},
        },
    )
    contract, gaps = NamedHandler().contract(item, 'jewel')
    assert contract is None
    assert any('ambiguous' in gap for gap in gaps)
