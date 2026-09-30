"""Decorated throwing labels require explicit facts, not a canonical-name match."""

import pytest

from pricing.knowledge.assessment.maintenance.qualified_table_context import require_qualification
from pricing.knowledge.definition_store import catalog


@pytest.mark.parametrize('name', ['Gimmershred', 'Warshrike', 'Lacerator', "Demon's Arch", "Gargoyle's Bite"])
def test_ethereal_throwing_label_requires_ethereal_rule(name):
    role = {'names': [name], 'must': {'all': [{'op': 'fact_eq', 'field': 'ethereal', 'value': True}]}}
    require_qualification(role, 'Ethereal ' + name)
    for predicate in ({}, {'op': 'fact_eq', 'field': 'ethereal', 'value': False}):
        with pytest.raises(ValueError, match='Table qualification'):
            require_qualification({**role, 'must': predicate}, 'Ethereal ' + name)


@pytest.mark.parametrize('name', ['Deathbit', 'The Scalper'])
def test_ethereal_upgraded_throwing_weapon_requires_both_facts(name):
    elite = catalog().named['unique', name]['base_definition']['ultracode']
    ethereal = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
    upgraded = {'op': 'fact_eq', 'field': 'base_code', 'value': elite}
    role = {'names': [name], 'must': {'all': [ethereal, upgraded]}}
    require_qualification(role, f'Ethereal {name} (Upgraded)')
    for predicate in (ethereal, upgraded, {'any': [ethereal, upgraded]}):
        with pytest.raises(ValueError, match='Table qualification'):
            require_qualification({**role, 'must': predicate}, f'Ethereal {name} (Upgraded)')


def test_ethereal_prefix_does_not_authorize_arbitrary_qualifications():
    role = {'names': ['Gimmershred'], 'must': {'op': 'fact_eq', 'field': 'ethereal', 'value': True}}
    with pytest.raises(ValueError, match='Table qualification'):
        require_qualification(role, 'Ethereal Gimmershred (Upgraded)')
