"""Offline source-occurrence census, including discovery and unresolved evidence.

A related rule is a review lead, not proof that a recommendation is implemented.
Run python -m pricing.knowledge.assessment.maintenance.inventory > audit.json.
"""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCOPE = ('build', 'variant', 'side', 'slot')


def audit_occurrences(occurrences, profiles):
    index = defaultdict(list)
    for profile in profiles:
        index[tuple(profile.get(key) for key in SCOPE)].append(profile)
    rows, seen = [], set()
    for occurrence in occurrences:
        identity = occurrence['id']
        if identity in seen:
            raise ValueError(f'Duplicate source occurrence: {identity}')
        seen.add(identity)
        details = occurrence.get('details', {})
        related = index.get(tuple(occurrence.get(key) for key in SCOPE), ())
        locator = occurrence.get('source_locator', '')
        source_rules = [
            p['id']
            for p in related
            if p['source']['path'] == occurrence.get('source_id')
            and (locator == p['source']['locator'] or locator.startswith(p['source']['locator'].rstrip('/') + '/'))
        ]
        status = (
            'discovery_only'
            if details.get('recommended') is False
            else 'endorsement_review'
            if details.get('recommended') is not True
            else 'identity_review'
            if details.get('resolution_status') != 'resolved'
            else 'rule_review'
        )
        rows.append(
            {
                **{
                    key: occurrence.get(key)
                    for key in ('id', 'name', 'original_label', *SCOPE, 'source_id', 'source_locator')
                },
                'status': status,
                'related_rule_ids': sorted(p['id'] for p in related),
                'source_rule_ids': sorted(source_rules),
            }
        )
    rows.sort(key=lambda row: row['id'])
    counts = Counter(row['status'] for row in rows)
    return {
        'schema_version': 1,
        'complete': False,
        'scope': (
            'Source occurrences, not deduplicated items. Rule links require semantic review; '
            'they do not establish complete coverage.'
        ),
        'counts': {
            'occurrences': len(rows),
            'builds': len({r['build'] for r in rows}),
            'build_variants': len({(r['build'], r['variant']) for r in rows}),
            'with_related_rules': sum(bool(r['related_rule_ids']) for r in rows),
            'with_source_rules': sum(bool(r['source_rule_ids']) for r in rows),
            **dict(sorted(counts.items())),
        },
        'rows': rows,
    }


def variant_occurrences(document, source, catalog):
    from pricing.knowledge.builds import resolve_named_label

    slug = document['slug']
    rows = []
    for number, variant in enumerate(document.get('variants', [])):
        for side in ('player', 'merc'):
            for slot, labels in variant.get(side, {}).items():
                if not isinstance(labels, list):
                    continue
                for ordinal, label in enumerate(labels):
                    if not isinstance(label, str):
                        raise ValueError(f'Invalid variant item label: {source}')
                    escaped = slot.replace('~', '~0').replace('/', '~1')
                    locator = f'/variants/{number}/{side}/{escaped}/{ordinal}'
                    resolved = resolve_named_label(label, catalog)
                    rows.append(
                        {
                            'id': hashlib.sha256(f'{source}:{slug}:{locator}'.encode()).hexdigest()[:24],
                            'name': resolved['name'] if resolved else label,
                            'original_label': label,
                            'build': slug,
                            'variant': variant['name'],
                            'side': side,
                            'slot': slot,
                            'source_id': source,
                            'source_locator': locator,
                            'details': {
                                'recommended': True,
                                'resolution_status': 'resolved' if resolved else 'pattern_or_unresolved',
                            },
                        }
                    )
    return rows


def main():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.builds import load_catalog

    demand_path = ROOT / 'pricing/data/appraisal-demand.json'
    raw = demand_path.read_bytes()
    occurrences = json.loads(raw)['rows']
    sources = {str(demand_path.relative_to(ROOT)): hashlib.sha256(raw).hexdigest()}
    catalog = load_catalog(ROOT)
    for path in sorted((ROOT / 'pricing/data/wp-a-variants').glob('*.json')):
        if path.name == 'index.json':
            continue  # Derived reverse lookup; source occurrences are already enumerated.
        raw = path.read_bytes()
        source = str(path.relative_to(ROOT))
        document = json.loads(raw)
        occurrences.extend(variant_occurrences(document, source, catalog))
        sources[source] = hashlib.sha256(raw).hexdigest()
    result = audit_occurrences(occurrences, build()['profiles'])
    result['input_hashes'] = sources
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
