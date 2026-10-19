"""Reconcile cached extractor spans, preserving skipped and conflicting evidence."""

from collections import defaultdict


def occurrence_source(source):
    """Map one pinned extractor span to its original guide-ledger reference.

    This only aligns identifiers. Existing source-hash, context and endorsement
    checks remain responsible for proving usable evidence. Whole sections and
    neighbouring spans must never inherit a pattern review through this mapping.
    """
    original = source['path'], source['locator']
    if source['path'] != 'pricing/data/appraisal-guide-sections.json':
        return original
    parts = source['locator'].split('/')
    if (
        len(parts) != 5
        or parts[:2] != ['', 'sources']
        or parts[3] != 'item_spans'
        or not parts[4].isdigit()
        or str(int(parts[4])) != parts[4]
    ):
        return original
    path = parts[2].replace('~1', '/').replace('~0', '~')
    if not path.startswith('pricing/raw/mr/') or not path.endswith('.html'):
        return original
    return path, '/item-spans/' + parts[4]


def audit_spans(mentions, source, occurrences, catalog):
    rows = [r for r in occurrences if r['source_id'] == source]
    index = defaultdict(list)
    for row in rows:
        index[row['source_locator']].append(row)
    spans, accounted = [], set()
    for ordinal, mention in enumerate(mentions):
        locator = f'/item-spans/{ordinal}'
        matches = [
            r['id']
            for r in index[locator]
            if r.get('details', {}).get('original_label') == mention['label']
            and r.get('details', {}).get('raw_item_id') == mention['item_id']
            and r.get('slot') == mention.get('slot')
            and r.get('side') == mention.get('side')
            and r.get('details', {}).get('profile_id') == mention.get('profile_id')
        ]
        status = 'represented' if matches else 'conflict' if index[locator] else 'missing_occurrence'
        if not index[locator] and not mention['label'] and mention['item_id'].split('-')[0] not in catalog:
            status = 'empty_unresolved_span'
        spans.append({'locator': locator, 'mention': mention, 'status': status, 'occurrence_ids': matches})
        accounted.update(matches)
    return {
        'source_id': source,
        'spans': spans,
        'complete': False,
        'unaccounted_occurrence_ids': sorted(r['id'] for r in rows if r['id'] not in accounted),
        'scope': 'Existing span extractor reconciliation; unmarked prose requires section review.',
    }
