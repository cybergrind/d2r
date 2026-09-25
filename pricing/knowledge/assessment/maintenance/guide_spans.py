"""Reconcile cached extractor spans, preserving skipped and conflicting evidence."""

from collections import defaultdict


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
