"""Capture facts with native stat identities; never use text as a semantic key."""

from functools import lru_cache
from types import SimpleNamespace

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.adapters.market_projection import market_properties, project_native
from pricing.knowledge.assessment.domain.facts import FactStatus, ItemFacts


REFERENCE_LEVEL = 90
# Structural totals/context aren't rolled market modifiers. Defense requires a
# dedicated named/armor contract; it is not priced by the v1 affixed handler.
STRUCTURAL_STATS = frozenset({21, 22, 23, 24, 31, 67, 68, 70, 72, 73, 194})


def bases_by_code():
    return _bases_by_code(metadata_generation())


@lru_cache(maxsize=2)
def _bases_by_code(generation):
    return {r['code']: r for r in metadata()['bases'].values()}


def normalize(extraction):
    item = extraction['item']
    base = bases_by_code().get(item.get('base_code'), {})
    source = extraction.get('source', {})
    facts = SimpleNamespace(
        name=item.get('name'),
        base_name=base.get('name'),
        base_code=item.get('base_code'),
        item_type=base.get('type'),
        rarity=item.get('rarity'),
        runeword=item.get('runeword'),
        identified=item.get('identified') if type(item.get('identified')) is bool else None,
        ethereal=item.get('ethereal') if type(item.get('ethereal')) is bool else None,
        sockets=item.get('sockets') if type(item.get('sockets')) is int and 0 <= item['sockets'] <= 6 else None,
        socket_contents=item.get('socket_contents') if item.get('socket_contents') in ('empty', 'filled') else None,
        socket_items=item.get('socket_items', []),
        filled_sockets=item.get('filled_sockets'),
        empty_sockets=item.get('empty_sockets'),
        item_level=item.get('item_level'),
        capture_complete=source.get('stat_capture_complete') is True,
        stats={},
        properties={},
        gaps=[],
        projection_gaps=[],
        provenance={'capture': source, 'base': 'inventory_tracking/items/data/item_metadata.json'},
    )
    if not base:
        facts.gaps.append('Unknown base identity/type; metadata required.')
    if base and item.get('base_name') not in (None, base['name']):
        facts.gaps.append('Captured base name conflicts with base code.')
    if item.get('item_type') not in (None, facts.item_type):
        facts.gaps.append('Captured item type conflicts with base metadata.')
    if not facts.capture_complete:
        facts.gaps.append('Stat capture completeness is unknown.')
    for key in ('identified', 'ethereal', 'sockets', 'socket_contents'):
        value = getattr(facts, key)
        if value is None or (key == 'identified' and not value):
            facts.gaps.append(f'{key} is unknown or unverified.')
    if facts.sockets == 0 and facts.socket_contents == 'filled':
        facts.gaps.append('Socket count conflicts with contents.')
    projected = {}
    market_catalog = market_properties()
    for affix in item.get('affixes', []):
        key = str(affix['property_id'])
        if key in facts.properties:
            facts.gaps.append(f'Duplicate market property {key}.')
        facts.properties[key] = affix['value']
        for raw in affix.get('memory_stats', [affix.get('memory_stat', {})]):
            if 'id' in raw:
                projected[f'{raw["id"]}:{raw["layer"]}'] = key
    for row in extraction.get('decoded_stats', []):
        for raw in row.get('memory_stats', [row.get('memory_stat', {})]):
            if 'id' not in raw:
                continue  # Explicitly derived base effects have no rolled identity.
            key = f'{raw["id"]}:{raw["layer"]}'
            if key in facts.stats:
                facts.gaps.append(f'Duplicate native stat {key}.')
            project_native(key, row, facts.properties, projected, facts.gaps, market_catalog)
            semantic = row.get('native_values', {}).get(key, row)
            fact = {
                'id': raw['id'],
                'parameter': raw['layer'],
                'raw': raw['raw'],
                'value': semantic.get('value'),
                'status': row.get('status'),
                'origin': row.get('origin', 'captured_total'),
                'name': row.get('name'),
                'text': row.get('text'),
                'unit': semantic.get('unit'),
                'market_property': projected.get(key),
            }
            if row.get('charges') is not None:
                fact['charges'] = row['charges']
            if row.get('per_level'):
                formula = row['per_level']
                fact.update(
                    per_level=formula,
                    viewer_level=row.get('viewer_level'),
                    reference_level=REFERENCE_LEVEL,
                    value_at_reference_level=raw['raw'] * REFERENCE_LEVEL // formula['denominator'],
                )
            facts.stats[key] = fact
            if row.get('status') != 'decoded':
                facts.gaps.append(f'Undecoded native stat {key}.')
            if raw['id'] not in STRUCTURAL_STATS and key not in projected:
                facts.projection_gaps.append(f'No verified market mapping for native stat {key}.')
    if extraction.get('unresolved_stats'):
        facts.gaps.append('Incomplete stat decoding.')
    if 'decoded_stats' not in extraction:
        facts.gaps.append('No native stat inventory; OCR facts require review.')
    result = ItemFacts(**vars(facts))
    if result.socket_state.total.status == FactStatus.CONFLICTING:
        facts.gaps.append('Socket occupancy conflicts with captured count or contents.')
        result = ItemFacts(**vars(facts))
    return result
