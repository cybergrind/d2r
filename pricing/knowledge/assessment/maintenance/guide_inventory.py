"""Item-centric guide review inventory; no inferred endorsements or demand grades.

Reuses the structured occurrence ledger. This is a maintenance checkpoint, not a
runtime artifact or proof that every cached source/slot has been extracted.
"""

import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy

from pricing.knowledge.assessment.maintenance.inventory import ROOT, audit_occurrences, collect_occurrences


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    ).hexdigest()


def configurations(profiles):
    groups = {}
    for profile in profiles:
        # Retain every non-provenance field conservatively: different conditions,
        # stage, side or preferences must not accidentally share a configuration.
        semantic = {k: v for k, v in profile.items() if k not in {'id', 'build', 'source', 'review_notes'}}
        key = fingerprint(semantic)
        group = groups.setdefault(
            key, {'id': key, 'configuration': deepcopy(semantic), 'profile_ids': [], 'sources': []}
        )
        group['profile_ids'].append(profile['id'])
        group['sources'].append({'profile_id': profile['id'], 'build': profile['build'], **deepcopy(profile['source'])})
    for group in groups.values():
        group['profile_ids'].sort()
        group['sources'].sort(key=lambda row: row['profile_id'])
    return [groups[key] for key in sorted(groups)]


def compile_inventory(occurrences, profiles, catalog):
    audit = audit_occurrences(occurrences, profiles)
    dispositions = {row['id']: row for row in audit['rows']}
    identities, by_name = {}, defaultdict(set)
    for catalog_id, entry in sorted(catalog.items()):
        key = fingerprint([entry['category'], entry['name']])
        row = identities.setdefault(
            key,
            {
                'id': key,
                'name': entry['name'],
                'category': entry['category'],
                'catalog_ids': [],
                'occurrence_ids': [],
                'review_state': 'pending',
            },
        )
        row['catalog_ids'].append(catalog_id)
        by_name[entry['name']].add(key)
    records = []
    for original in sorted(occurrences, key=lambda row: row['id']):
        row = deepcopy(original)
        candidates = by_name.get(row['name'], set())
        if row.get('category'):
            candidates = {key for key in candidates if identities[key]['category'] == row['category']}
        details = row.get('details', {})
        basis = 'canonical_name'
        canonical_id = details.get('canonical_id')
        if canonical_id is not None:
            entry = catalog.get(canonical_id)
            labels = {entry['name'], *entry.get('aliases', [])} if entry else set()
            prefix = {3: 'Magic ', 4: 'Rare ', 8: 'Crafted '}.get(details.get('quality'))
            if prefix and entry and entry['category'] in {'weapon', 'armor', 'misc'}:
                labels |= {prefix + label for label in labels}
            compatible = entry and row['name'] in labels and row.get('category') in {None, entry['category']}
            candidates = {fingerprint([entry['category'], entry['name']])} if compatible else set()
            basis = 'canonical_id' if compatible else 'canonical_id_conflict'
        resolved = details.get('resolution_status') == 'resolved' and len(candidates) == 1
        if resolved:
            key = next(iter(candidates))
        else:
            key = fingerprint(['unresolved', row.get('category'), row['name']])
            identities.setdefault(
                key,
                {
                    'id': key,
                    'name': row['name'],
                    'category': 'unresolved',
                    'catalog_ids': [],
                    'occurrence_ids': [],
                    'review_state': 'pending',
                },
            )
        identities[key]['occurrence_ids'].append(row['id'])
        disposition = dispositions[row['id']]
        row.update(
            identity_id=key,
            identity_status='resolved' if resolved else 'unresolved',
            identity_basis=basis,
            review_state=disposition['status'],
            related_rule_ids=disposition['related_rule_ids'],
            source_rule_ids=disposition['source_rule_ids'],
        )
        records.append(row)
    configs = configurations(profiles)
    return {
        'schema_version': 1,
        'extractor_version': 'guide-inventory-1',
        'complete': False,
        'limitations': [
            'Source/slot completeness, set expansion, aliases and recommendation strength still require audit.',
            'A source-rule link is a review lead, not a reviewed demand vote or captured-item match.',
        ],
        'counts': {
            **audit['counts'],
            'identity_buckets': len(identities),
            'catalog_identity_buckets': sum(bool(row['catalog_ids']) for row in identities.values()),
            'unresolved_occurrences': sum(row['identity_status'] != 'resolved' for row in records),
            'reviewed_profiles': len(profiles),
            'distinct_configurations': len(configs),
        },
        'identities': [identities[key] for key in sorted(identities)],
        'occurrences': records,
        'configurations': configs,
    }


def inspect_source(root, source):
    path = root / source['path']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {
        **source,
        'actual_sha256': actual,
        'status': 'verified' if actual is not None and actual == source.get('sha256') else 'changed_or_missing',
    }


def main():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.maintenance.embedded_items import resolve_embedded_item
    from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
    from pricing.knowledge.assessment.maintenance.guide_spans import audit_spans
    from pricing.knowledge.assessment.maintenance.planner_slots import audit_planner_slots
    from pricing.knowledge.assessment.maintenance.set_relationships import set_relationships
    from pricing.knowledge.assessment.maintenance.source_conflicts import source_conflicts
    from pricing.knowledge.assessment.maintenance.source_slots import audit_build_slots, audit_variant_slots
    from pricing.knowledge.assessment.maintenance.variant_contexts import variant_contexts
    from pricing.knowledge.builds import decode_planner
    from pricing.knowledge.refresh import atomic_json

    occurrences, inputs, catalog = collect_occurrences()
    definition_path = 'pricing/data/appraisal-definitions.json'
    definition_bytes = (ROOT / definition_path).read_bytes()
    definitions = json.loads(definition_bytes)
    if definitions.get('schema_version') != 1:
        raise ValueError('Unsupported item definition schema')
    inputs[definition_path] = hashlib.sha256(definition_bytes).hexdigest()
    profiles = build()
    result = compile_inventory(occurrences, profiles['profiles'], catalog)
    demand = json.loads((ROOT / 'pricing/data/appraisal-demand.json').read_text())
    if demand.get('schema_version') != 1:
        raise ValueError('Unsupported guide occurrence schema')
    sources = [inspect_source(ROOT, source) for source in demand['sources']]
    recorded = {s['path'] for s in sources}
    for path, digest in sorted(inputs.items()):
        if path not in recorded:
            sources.append(
                {
                    'id': path,
                    'path': path,
                    'sha256': digest,
                    'actual_sha256': digest,
                    'parser_version': 'guide-inventory-1',
                    'status': 'verified',
                }
            )
    sources.sort(key=lambda row: row['path'])
    source_states = {row['id']: row['status'] for row in sources}
    for row in result['occurrences']:
        row['source_status'] = source_states.get(row['source_id'], 'unregistered')
    result['set_relationships'] = set_relationships(occurrences, definitions['rows'])
    result['set_definition_provenance'] = {
        'path': definition_path,
        'sha256': inputs[definition_path],
        'source_date': definitions['source_date'],
        'inputs': definitions['inputs'],
    }
    result['counts']['set_relationship_states'] = dict(
        sorted(Counter(link['relationship'] for link in result['set_relationships']).items())
    )
    result['sources'] = sources
    result['input_hashes'] = inputs
    result['profile_fingerprint'] = fingerprint(profiles)
    result['source_coverage'] = demand['coverage']
    section_path = ROOT / 'pricing/data/appraisal-guide-sections.json'
    old_sections = json.loads(section_path.read_text()).get('sources', {}) if section_path.exists() else {}
    section_sources = {}
    for path in sorted((ROOT / 'pricing/raw/mr').glob('guides__*.html')):
        source = str(path.relative_to(ROOT))
        section_sources[source] = section_inventory(path.read_text(), old_sections.get(source))
    atomic_json(section_path, {'schema_version': 1, 'sources': section_sources})
    result['guide_section_inventory'] = {
        'path': str(section_path.relative_to(ROOT)),
        'sha256': hashlib.sha256(section_path.read_bytes()).hexdigest(),
        'sources': [
            {
                'path': path,
                'source_sha256': record['source_sha256'],
                'sections': len(record['sections']),
                'manifest_status': 'registered' if path in recorded else 'not_in_demand_manifest',
            }
            for path, record in section_sources.items()
        ],
    }
    span_audits = [
        audit_spans(record['item_spans'], source, occurrences, catalog) for source, record in section_sources.items()
    ]
    result['guide_span_audits'] = span_audits
    result['counts']['guide_span_states'] = dict(
        sorted(Counter(span['status'] for audit in span_audits for span in audit['spans']).items())
    )
    result['counts']['unaccounted_guide_occurrences'] = sum(
        len(audit['unaccounted_occurrence_ids']) for audit in span_audits
    )
    embedded_items = []
    planner_cache = {}
    for source, record in section_sources.items():
        for reference in record['embedded_item_refs']:
            planner_path = f'pricing/raw/mr/planners/{reference["profile_id"]}.json'
            if planner_path not in planner_cache:
                path = ROOT / planner_path
                try:
                    planner_cache[planner_path] = decode_planner(json.loads(path.read_text()))
                except OSError, ValueError:
                    planner_cache[planner_path] = None
            planner = planner_cache[planner_path]
            if planner is None:
                resolved = {
                    'reference': reference,
                    'status': 'missing_planner',
                    'review_state': 'pending',
                    'occurrence_ids': [],
                }
            else:
                resolved = resolve_embedded_item(
                    reference, planner, [r for r in occurrences if r['source_id'] == planner_path]
                )
            embedded_items.append({'source_id': source, 'planner_source_id': planner_path, **resolved})
    result['embedded_item_links'] = embedded_items
    result['source_conflicts'] = source_conflicts(embedded_items, planner_cache)
    result['counts']['distinct_source_conflicts'] = len(result['source_conflicts'])
    result['counts']['embedded_item_states'] = dict(sorted(Counter(row['status'] for row in embedded_items).items()))
    result['counts']['cached_guide_pages'] = len(section_sources)
    result['counts']['cached_guide_sections'] = sum(len(r['sections']) for r in section_sources.values())
    result['counts']['guide_pages_outside_manifest'] = sum(path not in recorded for path in section_sources)

    slot_audits = [
        audit_variant_slots(json.loads((ROOT / path).read_text()), path, occurrences)
        for path in sorted(inputs)
        if path.startswith('pricing/data/wp-a-variants/')
    ]
    build_path = 'pricing/data/wp-a-builds.json'
    consolidated = audit_build_slots(json.loads((ROOT / build_path).read_text()), build_path, occurrences)
    contexts = []
    for path in sorted(inputs):
        if path.startswith('pricing/data/wp-a-variants/'):
            contexts.extend(variant_contexts(json.loads((ROOT / path).read_text()), path))
    for slug, document in sorted(json.loads((ROOT / build_path).read_text()).items()):
        contexts.extend(variant_contexts({'slug': slug, **document}, build_path, prefix=f'/{slug}'))
    result['variant_contexts'] = contexts
    result['counts']['variant_demand_eligibility'] = dict(
        sorted(Counter(row['demand_eligibility'] for row in contexts).items())
    )
    result['counts']['variant_inheritance_states'] = dict(
        sorted(Counter(row['inheritance_status'] for row in contexts).items())
    )
    result['consolidated_slot_audit'] = consolidated
    result['counts']['consolidated_slot_states'] = dict(
        sorted(Counter(slot['status'] for slot in consolidated['slots']).items())
    )
    planner_audits = []
    for planner_id in sorted(demand['coverage']['planners']):
        path = f'pricing/raw/mr/planners/{planner_id}.json'
        planner_audits.append(audit_planner_slots(json.loads((ROOT / path).read_text()), path, occurrences))
    result['planner_slot_audits'] = planner_audits
    result['planner_source_gaps'] = demand['coverage']['unavailable_planners']
    result['counts']['planner_slot_states'] = dict(
        sorted(Counter(slot['status'] for audit in planner_audits for slot in audit['slots']).items())
    )
    result['counts']['planner_container_states'] = dict(
        sorted(Counter(container['status'] for audit in planner_audits for container in audit['containers']).items())
    )
    result['counts']['unaccounted_planner_occurrences'] = sum(
        len(audit['unaccounted_occurrence_ids']) for audit in planner_audits
    )
    result['variant_slot_audits'] = slot_audits
    result['counts']['variant_slot_states'] = dict(
        sorted(Counter(slot['status'] for audit in slot_audits for slot in audit['slots']).items())
    )
    result['counts']['variant_side_states'] = dict(
        sorted(Counter(side['status'] for audit in slot_audits for side in audit['sides']).items())
    )
    result['counts']['cached_guides'] = len(demand['coverage']['guides'])
    result['counts']['unregistered_source_occurrences'] = sum(
        row['source_status'] == 'unregistered' for row in result['occurrences']
    )
    result['counts']['changed_or_missing_sources'] = sum(s['status'] != 'verified' for s in sources)
    atomic_json(ROOT / 'pricing/data/appraisal-guide-inventory.json', result)
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
