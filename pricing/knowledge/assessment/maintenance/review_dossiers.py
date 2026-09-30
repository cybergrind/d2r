"""Compact offline review leads over the full census, never executable decisions.

Run with --identity NAME to expand evidence for an item (including unresolved
names), or omit it to write the complete review index. Rebuild guide_inventory
first when sources or profiles change. No raw extraction or network access here.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy

from pricing.knowledge.assessment.demand_counts import summarize_demand
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import configurations
from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
from pricing.knowledge.assessment.maintenance.inventory import ROOT


def _named_use_matches(identity, use, profiles):
    item = use.get('item')
    # The census groups the two native Hustle records under their shared name.
    # Attach reviewed variants to that parent only; their configurations and
    # source-specific armor/weapon requirements remain independent below.
    if (
        identity['category'] == 'runeword'
        and identity['name'] == 'Hustle'
        and item in ('Hustle (armor)', 'Hustle (weapon)')
    ):
        item = 'Hustle'
    if identity['category'] == 'unresolved' or item != identity['name']:
        return False
    qualities = {'runeword': {'normal', 'superior'}, 'unique': {'unique'}, 'set': {'set'}}
    allowed = qualities.get(identity['category'], set())
    return bool(allowed.intersection(profiles[use['profile_id']].get('qualities', [])))


def _review_leads(records):
    """Verified guide candidates, not endorsed uses or demand votes."""
    eligible = []
    for row in records:
        details = row.get('details', {})
        build = row.get('build')
        if (
            row.get('source_status') != 'verified'
            or row.get('review_state') == 'discovery_only'
            or details.get('historical')
            or details.get('recommended') is False
            or not build
            or build == 'shared-planner'
            or 'hardcore' in row.get('variant', '').casefold()
        ):
            continue
        eligible.append(row)
    builds = sorted({r['build'] for r in eligible})
    return {'builds': builds, 'distinct_builds': len(builds), 'occurrence_ids': sorted(r['id'] for r in eligible)}


def _review_queues(identities):
    queues = {
        key: []
        for key in (
            'new_named_identities',
            'named_use_expansion',
            'bases_and_patterns',
            'unresolved_identities',
            'no_verified_guide_leads',
        )
    }
    for row in sorted(identities, key=lambda r: (-r['review_leads']['distinct_builds'], r['name'], r['identity_id'])):
        if row.get('pattern_review_profile_ids'):
            key = 'bases_and_patterns'
        elif row['category'] == 'unresolved':
            key = 'unresolved_identities'
        elif not row['review_leads']['distinct_builds']:
            key = 'no_verified_guide_leads'
        elif row['category'] in {'unique', 'set', 'runeword'}:
            key = 'named_use_expansion' if row['guide_review_profile_ids'] else 'new_named_identities'
        else:
            key = 'bases_and_patterns'
        queues[key].append(row['identity_id'])
    return queues


def _pattern_bindings(records, uses, profiles, *, include_partial=False):
    """Bind explicit label reviews only to the exact verified guide occurrence."""
    eligible = set(_review_leads(records)['occurrence_ids'])
    bindings = []
    for use in uses:
        if use.get('source_coverage') and not include_partial:
            continue
        if not use.get('pattern_label') or not summarize_demand([use], complete=False)['distinct_builds']:
            continue
        role = profiles[use['profile_id']]
        source_id, source_locator = occurrence_source(use['source'])
        matched = [
            row['id']
            for row in records
            if row['id'] in eligible
            and row.get('original_label') == use['pattern_label']
            and row.get('source_id') == source_id
            and row.get('source_locator') == source_locator
            and (role['id'] in row['source_rule_ids'] or 'pattern_source_slot' in use)
            and all(row.get(key) == role.get(key) for key in ('build', 'variant', 'side'))
            and row.get('slot') == use.get('pattern_source_slot', role.get('slot'))
        ]
        if matched:
            bindings.append((use, matched))
    return bindings


def compile_dossiers(inventory, profiles, uses):
    """Reuse semantic configurations; occurrence links are not proof of membership."""
    configs = configurations(profiles)
    if configs != inventory['configurations']:
        raise ValueError('Stale inventory configurations; rebuild guide_inventory')
    compile_demand(uses, profiles)  # Enforce exact source and predicate review fingerprints.
    by_profile = {p['id']: p for p in profiles}
    config_for = {pid: c['id'] for c in configs for pid in c['profile_ids']}
    occurrences = {r['id']: r for r in inventory['occurrences']}
    if len(occurrences) != len(inventory['occurrences']):
        raise ValueError('Duplicate dossier occurrence')
    linked = defaultdict(set)
    for row in occurrences.values():
        for pid in row['source_rule_ids']:
            if pid not in config_for:
                raise ValueError(f'Unknown source rule: {pid}')
            linked[row['identity_id']].add(config_for[pid])
    identities = []
    component_uses = [u for u in uses if u.get('pattern_component')]
    for identity in inventory['identities']:
        records = [occurrences[i] for i in identity['occurrence_ids']]
        if any(r['identity_id'] != identity['id'] for r in records):
            raise ValueError('Conflicting dossier identity membership')
        reviewed = [u for u in uses if _named_use_matches(identity, u, by_profile)]
        named = identity['category'] in {'unique', 'set', 'runeword'}
        bindings = _pattern_bindings(records, component_uses if named else uses, by_profile, include_partial=True)
        components = (
            []
            if identity['category'] == 'runeword'
            else [(u, ids) for u, ids in bindings if u.get('pattern_component')]
        )
        patterns = [] if named else [(u, ids) for u, ids in bindings if not u.get('pattern_component')]
        pattern_uses = [use for use, _ in patterns]
        identities.append(
            {
                'identity_id': identity['id'],
                'name': identity['name'],
                'category': identity['category'],
                'catalog_ids': sorted(identity['catalog_ids']),
                'review_state': 'pending',
                'demand': summarize_demand([*reviewed, *pattern_uses], complete=False),
                'review_leads': _review_leads(records),
                'guide_review_profile_ids': sorted({u['profile_id'] for u in reviewed}),
                'guide_review_configuration_ids': sorted({config_for[u['profile_id']] for u in reviewed}),
                'pattern_review_profile_ids': sorted({u['profile_id'] for u in pattern_uses}),
                'pattern_review_configuration_ids': sorted({config_for[u['profile_id']] for u in pattern_uses}),
                'reviewed_pattern_occurrence_ids': sorted(
                    {oid for use, ids in patterns if not use.get('source_coverage') for oid in ids}
                ),
                'partial_pattern_reviews': [
                    {
                        'profile_id': use['profile_id'],
                        'occurrence_ids': sorted(ids),
                        'remaining_branches': use['source_coverage']['remaining_branches'],
                    }
                    for use, ids in patterns
                    if use.get('source_coverage')
                ],
                'component_reviews': [
                    {
                        **u['pattern_component'],
                        'profile_id': u['profile_id'],
                        'configuration_id': config_for[u['profile_id']],
                        'occurrence_ids': sorted(set(ids)),
                    }
                    for u, ids in sorted(components, key=lambda pair: pair[0]['profile_id'])
                ],
                'source_linked_configuration_ids': sorted(linked[identity['id']]),
                'occurrence_ids': sorted(identity['occurrence_ids']),
                'occurrence_states': dict(sorted(Counter(r['review_state'] for r in records).items())),
                'source_states': dict(sorted(Counter(r.get('source_status', 'unverified') for r in records).items())),
                'next_action': 'review_remaining_pattern_occurrences'
                if patterns
                else 'resolve_identity'
                if identity['category'] == 'unresolved'
                else ('review_source_requirements' if records else 'review_non_guide_evidence'),
                'estimated_review_minutes': None,
            }
        )
    identities.sort(key=lambda r: (-r['demand']['distinct_builds'], r['name'], r['identity_id']))
    return {
        'schema_version': 1,
        'complete': False,
        'limitations': [
            'Source-linked configurations are review leads, not confirmed applicability or coverage.',
            'Demand is a reviewed lower bound; pattern reviews cover only their exact verified occurrences.',
            'Socket-component reviews do not endorse the recipient identity or establish its socket contents.',
            'Review-lead breadth is unreviewed discovery, never endorsement, demand or a price signal.',
            'Separate new identities from expansion; reserve specialist/leveling work after two demand batches.',
            'Items without guide evidence remain in scope; no tier, price or no-use decision is inferred.',
            'Review effort is unestimated; demand order is not a substitute for specialist and leveling batches.',
        ],
        'counts': {'identities': len(identities), 'occurrences': len(occurrences), 'configurations': len(configs)},
        'identities': identities,
        'review_queues': _review_queues(identities),
        'configurations': configs,
        'source_conflicts': deepcopy(inventory.get('source_conflicts', [])),
        'reviewed_source_issues': deepcopy(inventory.get('reviewed_source_issues', [])),
        'planner_source_gaps': deepcopy(inventory.get('planner_source_gaps', [])),
    }


def expand_dossier(document, inventory, identity_id):
    dossier = next(row for row in document['identities'] if row['identity_id'] == identity_id)
    ids = set(dossier['occurrence_ids'])
    config_ids = (
        set(dossier['source_linked_configuration_ids'])
        | set(dossier['guide_review_configuration_ids'])
        | set(dossier.get('pattern_review_configuration_ids', []))
        | {r['configuration_id'] for r in dossier.get('component_reviews', [])}
    )
    return deepcopy(
        {
            **dossier,
            'occurrences': sorted((r for r in inventory['occurrences'] if r['id'] in ids), key=lambda r: r['id']),
            'configurations': [c for c in document['configurations'] if c['id'] in config_ids],
        }
    )


def verify_inputs(inventory, root):
    """Reject stale extraction instead of silently presenting obsolete evidence."""
    hashes = dict(inventory.get('input_hashes', {}))
    for source in inventory.get('sources', []):
        if source['path'] in hashes and hashes[source['path']] != source['sha256']:
            raise ValueError(f'Conflicting inventory hashes: {source["path"]}')
        hashes[source['path']] = source['sha256']
    for name, expected in hashes.items():
        path = root / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected or expected is None:
            raise ValueError(f'Stale inventory source: {name}; rebuild guide_inventory')


def main():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.refresh import atomic_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', help='Exact canonical or unresolved name; returns all category matches')
    args = parser.parse_args()
    path = ROOT / 'pricing/data/appraisal-guide-inventory.json'
    raw = path.read_bytes()
    inventory = json.loads(raw)
    if inventory.get('schema_version') != 1 or inventory.get('extractor_version') != 'guide-inventory-1':
        raise ValueError('Unsupported guide inventory; rebuild guide_inventory')
    verify_inputs(inventory, ROOT)
    review_path = ROOT / 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
    review_raw = review_path.read_bytes()
    reviews = json.loads(review_raw)
    if reviews.get('schema_version') != 1:
        raise ValueError('Unsupported guide review schema')
    result = compile_dossiers(inventory, build()['profiles'], reviews['uses'])
    result['inputs'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(raw).hexdigest(),
        str(review_path.relative_to(ROOT)): hashlib.sha256(review_raw).hexdigest(),
    }
    if args.identity:
        matches = [r for r in result['identities'] if r['name'].casefold() == args.identity.casefold()]
        if not matches:
            parser.error(f'No census identity named {args.identity!r}')
        print(json.dumps([expand_dossier(result, inventory, r['identity_id']) for r in matches], indent=2))
    else:
        atomic_json(ROOT / 'pricing/data/appraisal-review-dossiers.json', result)
        print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
