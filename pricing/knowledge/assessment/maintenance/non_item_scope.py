"""Source-checked non-item placeholders; never exclude an actual catalog identity."""

import hashlib
import json


SOURCE = 'pricing/data/wp-a-builds.json'
# Individually reviewed consolidated mercenary table cells. Other uses of N/A,
# prose, and decorated item labels are not covered by this review.
REVIEWED_SLOTS = {
    '/fissure-druid/merc/Shield/early/0': 'early',
    '/fissure-druid/merc/Shield/mid/0': 'mid',
}


def empty_slot_exclusions(inventory, root):
    identities = {r['id']: r for r in inventory['identities']}
    candidates = []
    for ordinal, row in enumerate(inventory['occurrences']):
        identity = identities.get(row.get('identity_id'), {})
        stage = REVIEWED_SLOTS.get(row.get('source_locator'))
        if (
            stage is not None
            and row.get('source_id') == SOURCE
            and row.get('source_status') == 'verified'
            and row.get('name') == row.get('original_label') == 'N/A'
            and row.get('identity_status') == 'unresolved'
            and row.get('category') is None
            and row.get('kind') == 'demand'
            and row.get('build') == 'fissure-druid'
            and row.get('variant') == stage
            and row.get('side') == 'merc'
            and row.get('slot') == 'Shield'
            and identity.get('name') == 'N/A'
            and identity.get('category') == 'unresolved'
            and identity.get('catalog_ids') == []
        ):
            candidates.append((ordinal, row, stage))
    if not candidates:
        return {}, {}
    sources = [s for s in inventory.get('sources', []) if s.get('id') == SOURCE and s.get('path') == SOURCE]
    try:
        raw = (root / SOURCE).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if (
            len(sources) != 1
            or sources[0].get('status') != 'verified'
            or not (sources[0].get('sha256') == sources[0].get('actual_sha256') == digest)
        ):
            raise ValueError('Unverified empty-slot source')
        document = json.loads(raw)
        for _, _, stage in candidates:
            if document['fissure-druid']['merc']['Shield'][stage][0] != 'N/A':
                raise ValueError('Conflicting empty-slot source')
    except (OSError, KeyError, IndexError, TypeError, ValueError) as error:
        raise ValueError('Missing, stale or conflicting empty-slot source') from error
    excluded = {
        row['id']: {
            'id': row['id'],
            'state': 'excluded',
            'identity_id': row['identity_id'],
            'reason': 'Reviewed N/A mercenary shield cell denotes no item; source occurrence retained.',
            'source': {'artifact': 'inventory', 'locator': f'/occurrences/{ordinal}'},
            'source_id': SOURCE,
            'source_locator': row['source_locator'],
            'source_sha256': digest,
        }
        for ordinal, row, _ in candidates
    }
    non_items = {}
    for key in {row['identity_id'] for row in excluded.values()}:
        identity = identities[key]
        actual = {r['id'] for r in inventory['occurrences'] if r.get('identity_id') == key}
        declared = identity.get('occurrence_ids', [])
        if actual and len(declared) == len(set(declared)) and actual == set(declared) and actual <= excluded.keys():
            non_items[key] = {
                'id': key,
                'state': 'excluded',
                'occurrence_ids': sorted(actual),
                'reason': 'Every occurrence of this unresolved bucket is a source-checked empty slot, not an item.',
            }
    return excluded, non_items
