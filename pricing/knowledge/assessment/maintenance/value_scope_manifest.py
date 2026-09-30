"""Exhaustive conservative scope membership; assessment evidence stays separate.

Callers supply exclusions already validated against source evidence. Historical
or unendorsed records are retained unless such an explicit exclusion applies.
"""

from collections import Counter

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.value_scope import SCOPE


def build_manifest(
    inventory,
    profiles,
    bases,
    policy,
    *,
    excluded_uses,
    excluded_occurrences,
    non_item_identities,
    matrix=None,
    seasonal_audit=None,
    excluded_evidence=None,
):
    if policy.get('scope') != SCOPE or policy.get('schema_version') != 1:
        raise ValueError('Scope manifest requires the current value-focused policy')
    members = {}
    excluded_evidence = excluded_evidence or {}

    def add(kind, entity, exclusion=None, *, key=None):
        key = key or kind + ':' + entity['id']
        if key in members:
            raise ValueError('Scope manifest duplicate member: ' + key)
        members[key] = {
            'id': key,
            'kind': kind,
            'entity_sha256': fingerprint(entity),
            'state': 'excluded' if exclusion else 'retained',
            'reason': exclusion['reason']
            if exclusion
            else ('Retain value and exceptional-leveling assessment obligations; no validated exclusion applies.'),
            'exclusion': exclusion,
        }

    for entity in inventory['identities']:
        add('identity', entity, non_item_identities.get(entity['id']))
    for entity in inventory['occurrences']:
        add('occurrence', entity, excluded_occurrences.get(entity['id']))
    for entity in (bases or {}).get('rows', []):
        add('base', entity)
    use_ids = {}
    for role in profiles:
        if role['id'] in use_ids:
            raise ValueError('Scope manifest duplicate profile')
        use_ids[role['id']] = []
        for quality in role['qualities']:
            identifier = role['id'] + ':' + quality
            key = 'use:' + identifier
            use_ids[role['id']].append(key)
            add('use', {'id': identifier, 'profile': role, 'quality': quality}, excluded_uses.get(key))
    for entity in inventory.get('configurations', []):
        refs = entity.get('profile_ids', [])
        if not refs or any(pid not in use_ids for pid in refs):
            raise ValueError('Scope manifest configuration lacks its profile membership')
        uses = [key for pid in refs for key in use_ids[pid]]
        exclusion = None
        if uses and all(key in excluded_uses for key in uses):
            exclusion = {
                'reason': 'Every use of this semantic configuration has a validated scope exclusion.',
                'use_ids': sorted(uses),
            }
        add('configuration', entity, exclusion)
    coverage_ids = set()
    for row in (matrix or {}).get('rows', []):
        key = row['id']
        if key in coverage_ids:
            raise ValueError('Scope manifest duplicate coverage row')
        coverage_ids.add(key)
        if key not in members:
            add(row.get('kind', 'coverage'), row, excluded_evidence.get(key), key=key)
    for conflict in (seasonal_audit or {}).get('rows', []):
        add('definition_conflict', conflict, key='seasonal_definition:' + conflict['table_key'])
    for keys, prefix in (
        (excluded_uses, ''),
        (excluded_evidence, ''),
        (excluded_occurrences, 'occurrence:'),
        (non_item_identities, 'identity:'),
    ):
        if any(prefix + key not in members for key in keys):
            raise ValueError('Scope manifest exclusion has no corresponding member')
    rows = [members[key] for key in sorted(members)]
    return {
        'schema_version': 1,
        'scope': SCOPE,
        'purpose': 'Scope membership only; retained members still require their independent assessment evidence.',
        'input_fingerprints': {
            key: fingerprint(value)
            for key, value in {
                'inventory': inventory,
                'profiles': profiles,
                'bases': bases,
                'policy': policy,
                'matrix': matrix,
                'seasonal_audit': seasonal_audit,
                'excluded_uses': excluded_uses,
                'excluded_evidence': excluded_evidence,
                'excluded_occurrences': excluded_occurrences,
                'non_item_identities': non_item_identities,
            }.items()
        },
        'counts': {
            'members': len(rows),
            'by_kind': dict(sorted(Counter(row['kind'] for row in rows).items())),
            'by_state': dict(sorted(Counter(row['state'] for row in rows).items())),
        },
        'members': rows,
    }
