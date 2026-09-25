from dataclasses import replace

from pricing.knowledge.assessment.handlers.definitions import named_definitions, resolve_named_definition
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_named_upgrade_requires_table_identity_and_same_ascending_base_chain():
    definition = named_definitions()['unique', 'Shaftstop']
    item = facts('Boneweave', 'unique', 'Shaftstop')
    assert resolve_named_definition(item)[0] is None
    verified = replace(
        item, provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': definition['table_id']}}}
    )
    assert resolve_named_definition(verified)[0] == definition
    for base in ('Chain Mail', 'Archon Plate'):
        changed = replace(verified, base_code=facts(base).base_code)
        assert resolve_named_definition(changed)[0] is None
    wrong_identity = replace(verified, provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': -1}}})
    assert resolve_named_definition(wrong_identity)[0] is None
