"""Named jewelry comparison contracts built from explicit native stats, for comparables tests."""

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.definition_store import catalog


# Copied from the archived fixed_jewelry_market_review (2026-10-19) so live tests keep this fixture.
def native_jewelry_contract(name, values, *, extra_raw=()):
    """Decode an explicitly reviewed jewelry configuration."""
    definition = catalog().named['unique', name]
    base = definition['base_definition']
    raw = [
        {'id': stat, 'layer': 0, 'raw': value << metadata()['stats'][str(stat)]['shift']}
        for stat, value in values.items()
    ]
    raw.extend(extra_raw)
    decoded, affixes, unresolved = decode_stats(raw, base=base)
    facts = normalize(
        {
            'item': {
                'name': name,
                'base_name': base['name'],
                'base_code': base['code'],
                'rarity': 'unique',
                'affixes': affixes,
                'identified': True,
                'ethereal': False,
                'sockets': 0,
                'socket_contents': 'empty',
                'socket_items': [],
            },
            'source': {
                'stat_capture_complete': True,
                'kind': 'reviewed_definition_template',
                'item_identity': {'table': 'unique', 'table_id': definition['game_definition']['*ID']},
            },
            'decoded_stats': decoded,
            'unresolved_stats': unresolved,
        }
    )
    contract, gaps = NamedHandler().contract(facts, 'jewelry')
    if contract is None or gaps:
        raise ValueError(f'Fixed jewelry comparison incomplete for {name}: {gaps}')
    return contract.to_dict()
