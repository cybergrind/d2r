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
from pricing.knowledge.assessment.maintenance.material_market_review import apply_material_market_reviews
from pricing.knowledge.assessment.maintenance.potion_market_review import apply_potion_market_reviews
from pricing.knowledge.assessment.maintenance.quest_material_market_review import apply_quest_material_market_reviews
from pricing.knowledge.assessment.maintenance.recipe_applicability import apply_recipe_applicability
from pricing.knowledge.assessment.maintenance.scroll_market_review import apply_scroll_market_reviews
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
    'trade_qualification',
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
    named_gate=None,
    recipe_applicability=None,
    pattern_reviews=None,
    uses=None,
    table_reviews=None,
    source_context_reviews=None,
    hardcore_reviews=None,
    material_market_reviews=None,
    potion_market_reviews=None,
    scroll_market_reviews=None,
    quest_material_market_reviews=None,
    fixed_jewelry_market_reviews=None,
    variable_jewelry_market_reviews=None,
    report_reviews=None,
    report_receipts=None,
    report_generation=None,
    report_inputs=None,
    trade_reviews=None,
    trade_context=None,
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
    collections = {}
    if pattern_reviews is not None:
        from pricing.knowledge.assessment.maintenance.pattern_collections import compile_collections

        collections = compile_collections(
            pattern_reviews,
            inventory,
            profiles['profiles'],
            uses['uses'],
            table_reviews,
            source_root,
            context_reviews=source_context_reviews,
            hardcore_reviews=hardcore_reviews,
        )
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
        if collection := collections.get(identity['id']):
            dims['discovery'] = dimension(
                'reviewed',
                collection['reason'],
                {'artifact': 'pattern_reviews', 'locator': f'/rows/{collection["review_index"]}'},
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
        elif (
            collection
            and collection['qualities']
            and set(collection['qualities']) <= {'low_quality', 'normal', 'superior', 'magic', 'rare', 'crafted'}
        ):
            dims['named_tiers'] = dimension(
                'excluded',
                'Every validated collection member is explicitly non-unique/non-set.',
                {'artifact': 'pattern_reviews', 'locator': f'/rows/{collection["review_index"]}'},
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
    from pricing.knowledge.assessment.maintenance.named_matrix import apply_named_dimensions

    apply_named_dimensions(rows, named_gate)
    apply_recipe_applicability(rows, recipe_applicability, source_root)
    apply_material_market_reviews(rows, material_market_reviews, source_root)
    apply_potion_market_reviews(rows, potion_market_reviews, source_root)
    apply_scroll_market_reviews(rows, scroll_market_reviews, source_root)
    apply_quest_material_market_reviews(rows, quest_material_market_reviews, source_root)
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import apply_reviews

    apply_reviews(rows, fixed_jewelry_market_reviews, source_root)
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import apply_reviews as apply_variable

    apply_variable(rows, variable_jewelry_market_reviews, source_root)
    accepted_report_receipts = set()
    if report_reviews is not None:
        from pricing.knowledge.assessment.maintenance.report_reviews import apply_report_reviews

        accepted_report_receipts = apply_report_reviews(
            rows, report_reviews, profiles, report_receipts or {}, report_generation, report_inputs or {}
        )
    accepted_trade_receipts = set()
    if trade_reviews is not None:
        from pricing.knowledge.assessment.maintenance.trade_reviews import apply_trade_reviews

        if trade_context is None:
            raise ValueError('Trade reviews require a published execution context')
        accepted_trade_receipts = apply_trade_reviews(rows, trade_reviews, **trade_context)
    rows.sort(key=lambda r: r['id'])
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate coverage row')
    dimensions = sorted({key for r in rows for key in r['dimensions']})
    return {
        'schema_version': 1,
        'report_receipts': sorted(accepted_report_receipts),
        'trade_receipts': sorted(accepted_trade_receipts),
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
        'named_gate': ROOT / 'pricing/data/appraisal-named-gate.json',
        'profiles': ROOT / 'pricing/data/appraisal-build-profiles.json',
        'recommendations': ROOT / 'pricing/data/appraisal-recommendations.json',
        'valuable': ROOT / 'pricing/data/appraisal-value-watch.json',
        'observed': ROOT / 'pricing/data/appraisal-observed-review.json',
        'material_market_reviews': ROOT / 'pricing/data/appraisal-material-market-review.json',
        'potion_market_reviews': ROOT / 'pricing/data/appraisal-potion-market-review.json',
        'scroll_market_reviews': ROOT / 'pricing/data/appraisal-scroll-market-review.json',
        'quest_material_market_reviews': ROOT / 'pricing/data/appraisal-quest-material-market-review.json',
        'fixed_jewelry_market_reviews': ROOT / 'pricing/data/appraisal-fixed-jewelry-market-review.json',
        'variable_jewelry_market_reviews': ROOT / 'pricing/data/appraisal-variable-jewelry-market-review.json',
        'stat_dispositions': ROOT / 'pricing/knowledge/assessment/rules/stat_dispositions.json',
        'recipe_applicability': ROOT / 'pricing/knowledge/assessment/rules/recipe_applicability.json',
        'pattern_reviews': ROOT / 'pricing/knowledge/assessment/rules/pattern_collection_reviews.json',
        'uses': ROOT / 'pricing/knowledge/assessment/rules/guide_use_reviews.json',
        'table_reviews': ROOT / 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json',
        'source_context_reviews': ROOT / 'pricing/knowledge/assessment/rules/source_context_reviews.json',
        'hardcore_reviews': ROOT / 'pricing/knowledge/assessment/rules/hardcore_reviews.json',
    }
    report_path = ROOT / 'pricing/knowledge/assessment/rules/report_reviews.json'
    if report_path.is_file():
        paths['report_reviews'] = report_path
    trade_path = ROOT / 'pricing/knowledge/assessment/rules/trade_qualification_reviews.json'
    if trade_path.is_file():
        paths['trade_reviews'] = trade_path
    raw = {key: path.read_bytes() for key, path in paths.items()}
    docs = {key: json.loads(value) for key, value in raw.items()}
    validate_inputs(docs, ROOT)
    from pricing.knowledge.assessment.maintenance.leveling_links import compile_leveling_links

    report_context = {}
    if 'report_reviews' in docs:
        from pricing.knowledge.assessment.maintenance.report_reviews import load_review_context

        receipts, generation, inputs = load_review_context(ROOT, docs['report_reviews'], docs['profiles'])
        report_context = {'report_receipts': receipts, 'report_generation': generation, 'report_inputs': inputs}
    if 'trade_reviews' in docs:
        from pricing.knowledge.assessment.maintenance.trade_reviews import load_context

        report_context['trade_context'] = load_context(ROOT, docs['trade_reviews'])
    result = build_matrix(**docs, **report_context, leveling_links=compile_leveling_links(docs['recommendations']))
    result['sources'] = {
        key: {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw[key]).hexdigest()}
        for key, path in paths.items()
    }
    for relative in sorted(set(result['report_receipts']) | set(result['trade_receipts'])):
        result['sources']['receipt:' + relative] = {
            'path': relative,
            'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
        }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
