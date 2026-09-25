"""Maintenance union of identity, base-quality and reviewed-use coverage ledgers.

Row kinds have separate denominators: an identity and its uses are not extra items.
Nothing here establishes captured-item fit or a numerical price.
"""

import hashlib
import json
from collections import Counter

from pricing.knowledge.assessment.maintenance.coverage_evidence import evidence_records
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.stat_dispositions import validate_stat_dispositions
from pricing.knowledge.assessment.stat_bundle import validate_stat_bundle


DIMENSIONS = (
    'discovery',
    'socket_mechanics',
    'recipe_eligibility',
    'desirability',
    'stat_desirability',
    'stat_annotations',
    'named_tiers',
    'leveling',
    'report',
    'market',
)


def dimension(state, reason, source):
    return {'state': state, 'reason': reason, 'sources': [source]}


def pending(source):
    return {
        key: dimension('pending', 'No complete reviewed evidence for this dimension.', source) for key in DIMENSIONS
    }


def build_matrix(
    inventory,
    bases,
    tiers,
    profiles,
    *,
    recommendations=None,
    valuable=None,
    observed=None,
    leveling_links=None,
    stat_dispositions=(),
    source_root=ROOT,
):
    validate_stat_bundle(profiles)
    exclusions = validate_stat_dispositions(stat_dispositions, profiles, root=source_root)
    identities = {r['id']: r for r in inventory['identities']}
    if len(identities) != len(inventory['identities']):
        raise ValueError('Duplicate inventory identity')
    if any(o['identity_id'] not in identities for o in inventory['occurrences']):
        raise ValueError('Occurrence references a missing identity')
    policies = {}
    for index, policy in enumerate(tiers['rows']):
        key = (policy['quality'], policy['name'])
        if key in policies:
            raise ValueError('Duplicate named tier identity')
        policies[key] = (index, policy)
    rows = []
    for index, identity in enumerate(identities.values()):
        source = {'artifact': 'inventory', 'locator': f'/identities/{index}'}
        dims = pending(source)
        resolved = bool(identity.get('catalog_ids')) and identity['category'] != 'unresolved'
        dims['discovery'] = dimension(
            'reviewed' if resolved else 'blocked',
            'Catalog identity retained.' if resolved else 'Identity/pattern resolution remains open.',
            source,
        )
        if identity['category'] in ('unique', 'set'):
            entry = policies.get((identity['category'], identity['name']))
            if entry:
                index, policy = entry
                state = (
                    'blocked'
                    if policy.get('source_error')
                    else ('reviewed' if policy['status'] == 'reviewed_policy' else 'pending')
                )
                dims['named_tiers'] = dimension(
                    state,
                    'Named tier audit: ' + policy['status'],
                    {
                        'artifact': 'tiers',
                        'locator': f'/rows/{index}',
                        'research_locator': policy.get('research_locator'),
                    },
                )
        elif identity['category'] != 'unresolved':
            dims['named_tiers'] = dimension('excluded', 'Not a unique/set identity.', source)
        rows.append(
            {
                'id': 'identity:' + identity['id'],
                'kind': 'identity',
                'name': identity['name'],
                'category': identity['category'],
                'catalog_ids': identity.get('catalog_ids', []),
                'occurrence_ids': sorted(set(identity.get('occurrence_ids', []))),
                'dimensions': dims,
            }
        )
    for index, base in enumerate(bases['rows']):
        source = {'artifact': 'bases', 'locator': f'/rows/{index}'}
        dims = pending(source)
        for key, value in base['dimensions'].items():
            dims[key] = dimension(value['state'], value['reason'], source)
        dims['leveling'] = dimension('pending', 'Base leveling uses need separate review.', source)
        rows.append(
            {
                'id': 'base:' + base['id'],
                'kind': 'base_quality',
                'name': base['name'],
                'base_code': base['base_code'],
                'quality': base['quality'],
                'candidate_profile_ids': base.get('candidate_profile_ids', []),
                'policy_assignments': base.get('policy_assignments', []),
                'base_uses': base.get('base_uses', []),
                'dimensions': dims,
            }
        )
    annotations = {c['role_id']: c for c in profiles.get('stat_evaluation', {}).get('configurations', [])}
    for index, role in enumerate(profiles['profiles']):
        source = {'artifact': 'profiles', 'locator': f'/profiles/{index}', 'evidence': role['source']}
        for quality in role['qualities']:
            dims = pending(source)
            dims['discovery'] = dimension('reviewed', 'Existing executable use retained.', source)
            dims['desirability'] = dimension(
                'reviewed' if role.get('review_status') == 'reviewed_candidate_rule' else 'pending',
                'Use rule review only; not identity-wide coverage or captured-item fit.',
                source,
            )
            config = annotations.get(role['id'])
            if config and config['review_state'] == 'reviewed':
                dims['stat_desirability'] = dimension(
                    'reviewed',
                    'Source-bound stat priorities compiled.',
                    {
                        'artifact': 'profiles',
                        'configuration_id': config['id'],
                        'version': config['version'],
                    },
                )
            if role['id'] in exclusions:
                dims['stat_desirability'] = exclusions[role['id']]
            dims['stat_annotations'] = dimension(
                'pending',
                'Desirability priorities alone do not complete roll and combined-line annotations.',
                source,
            )
            rows.append(
                {
                    'id': f'use:{role["id"]}:{quality}',
                    'kind': 'use_quality',
                    'profile_id': role['id'],
                    'quality': quality,
                    'types': role.get('types', []),
                    'names': role.get('names', []),
                    'dimensions': dims,
                }
            )
    identity_rows = {r['id']: r for r in rows if r['kind'] == 'identity'}
    for record in evidence_records(identities, recommendations or {}, valuable or {}):
        source = record['source']
        dims = pending(source)
        dims['discovery'] = dimension(
            'reviewed' if record['identity_ids'] else 'blocked',
            'Exact name and quality identify one catalog row.'
            if record['identity_ids']
            else 'Missing or ambiguous identity; retain evidence for explicit review.',
            source,
        )
        evidence = record['evidence']
        if (
            record['evidence_kind'] == 'leveling'
            and record['identity_ids']
            and evidence.get('purpose') == 'leveling'
            and evidence.get('evidence_strength') in {'reviewed_inference', 'explicit'}
            and evidence.get('review')
        ):
            dims['leveling'] = dimension(
                'reviewed',
                'Reviewed conditional leveling use; not exhaustive identity-wide coverage.',
                source,
            )
        policy = (leveling_links or {}).get(fingerprint(evidence))
        if record['evidence_kind'] == 'leveling_pattern' and policy:
            record['policy_links'] = [policy]
            for key in ('discovery', 'leveling'):
                dims[key] = dimension(
                    'reviewed',
                    'Exact cached pattern linked to existing conditional policy.',
                    {
                        **source,
                        'policy_id': policy['id'],
                        'policy_source': policy['source'],
                    },
                )
        record['dimensions'] = dims
        for identity_id in record['identity_ids']:
            identity_rows[identity_id].setdefault('evidence_ids', []).append(record['id'])
        rows.append(record)
    for index, capture in enumerate((observed or {}).get('captures', [])):
        source = {
            'artifact': 'observed',
            'locator': f'/captures/{index}',
            'capture_source': capture['source'],
            'capture_sha256': capture['capture_sha256'],
            'revision': capture['latest_revision'],
        }
        dims = pending(source)
        dims['discovery'] = dimension('reviewed', 'Historical capture retained; not current inventory.', source)
        for gap in capture['gaps']:
            key = gap['dimension']
            if key not in dims or 'gap_reasons' not in dims[key]:
                dims[key] = dimension('pending', 'Observed replay gap needs review.', source)
                dims[key]['gap_reasons'] = []
            dims[key]['gap_reasons'].append(gap['reason'])
        rows.append(
            {
                'id': 'capture:' + capture['id'],
                'kind': 'observed_capture',
                'facts': capture['facts'],
                'dimensions': dims,
            }
        )
    rows.sort(key=lambda r: r['id'])
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate coverage row')
    dimensions = sorted({key for r in rows for key in r['dimensions']})
    return {
        'schema_version': 1,
        'complete': False,
        'limitations': [
            'Identity, base-quality and use-quality rows are separate denominators, not additive item counts.',
            'Source inventories remain incomplete; unreviewed patterns are retained, not assumed worthless.',
            'Observed capture coverage is limited to imported replays; exact template membership remains pending.',
            'Market counts and source mentions do not establish exact matched prices.',
        ],
        'review_queues': {
            key: [
                {'row_id': r['id'], **r['dimensions'][key]}
                for r in rows
                if key in r['dimensions'] and r['dimensions'][key]['state'] in {'pending', 'blocked'}
            ]
            for key in dimensions
        },
        'counts': {
            'by_kind': dict(sorted(Counter(r['kind'] for r in rows).items())),
            'unlinked_evidence': sum(
                r['kind'] == 'evidence' and not r['identity_ids'] and not r.get('policy_links') for r in rows
            ),
            'dimensions_by_kind': {
                kind: {
                    key: dict(
                        sorted(
                            Counter(
                                r['dimensions'][key]['state']
                                for r in rows
                                if r['kind'] == kind and key in r['dimensions']
                            ).items()
                        )
                    )
                    for key in dimensions
                }
                for kind in sorted({r['kind'] for r in rows})
            },
        },
        'rows': rows,
    }


def validate_inputs(docs, root):
    hashes = dict(docs['inventory']['input_hashes'])
    for source in docs['bases']['sources'].values():
        if source['path'] in hashes and hashes[source['path']] != source['sha256']:
            raise ValueError('Conflicting source snapshots')
        hashes[source['path']] = source['sha256']
    for key in ('recommendations', 'valuable'):
        for name, digest in docs.get(key, {}).get('inputs', {}).items():
            if name in hashes and hashes[name] != digest:
                raise ValueError('Conflicting source snapshots')
            hashes[name] = digest
    for capture in docs.get('observed', {}).get('captures', []):
        name, digest = capture['source'], capture['capture_sha256']
        if name in hashes and hashes[name] != digest:
            raise ValueError('Conflicting source snapshots')
        hashes[name] = digest
    for name, digest in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f'Missing source snapshot: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Stale source snapshot: {name}')
    if docs['inventory']['profile_fingerprint'] != fingerprint(docs['profiles']):
        raise ValueError('Stale guide profile snapshot; rebuild guide_inventory')


def main():
    paths = {
        'inventory': ROOT / 'pricing/data/appraisal-guide-inventory.json',
        'bases': ROOT / 'pricing/data/appraisal-base-matrix.json',
        'tiers': ROOT / 'pricing/data/appraisal-tier-coverage.json',
        'profiles': ROOT / 'pricing/data/appraisal-build-profiles.json',
        'recommendations': ROOT / 'pricing/data/appraisal-recommendations.json',
        'valuable': ROOT / 'pricing/data/appraisal-value-watch.json',
        'observed': ROOT / 'pricing/data/appraisal-observed-review.json',
        'stat_dispositions': ROOT / 'pricing/knowledge/assessment/rules/stat_dispositions.json',
    }
    raw = {key: path.read_bytes() for key, path in paths.items()}
    docs = {key: json.loads(value) for key, value in raw.items()}
    validate_inputs(docs, ROOT)
    from pricing.knowledge.assessment.maintenance.leveling_links import compile_leveling_links

    result = build_matrix(**docs, leveling_links=compile_leveling_links(docs['recommendations']))
    result['sources'] = {
        key: {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw[key]).hexdigest()}
        for key, path in paths.items()
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
