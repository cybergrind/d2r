"""Image-to-local-evidence pipeline; the calling agent reviews and appraises the draft."""

import time

from pricing.knowledge.index import compact_result, lookup, search


def retrieve_draft(extraction, database):
    """Retrieve candidate evidence without promoting OCR readings to verified facts."""
    started = time.perf_counter()
    item = extraction['item']
    facets = {
        key: item[key] for key in ('sockets', 'rarity', 'ethereal', 'socket_contents') if item.get(key) is not None
    }
    properties = {row['property_id']: row['value'] for row in item.get('affixes', [])}
    if properties:
        facets['properties'] = properties
    queries = []
    evidence = {}
    if item.get('name'):
        queries.append({'purpose': 'identity_candidates', 'name': item['name'], 'facets': facets})
        evidence['identity'] = compact_result(lookup(database, item['name'], **facets, limit=3))
    for row in item.get('affixes', []):
        if 'Only)' not in row.get('label', ''):
            continue
        skill_facets = {'property_min': {row['property_id']: row['value']}}
        queries.append({'purpose': 'cross_base_skill_discovery', 'facets': skill_facets})
        evidence.setdefault('skills', []).append(compact_result(search(database, limit=3, **skill_facets)))
    return {
        'offline': True,
        'appraisal_ready': False,
        'extraction': extraction,
        'queries': queries,
        'evidence': evidence,
        'decision': {
            'verdict': 'REVIEW',
            'price_status': 'unresolved',
            'reason': 'Review OCR against the image; retrieved records are candidate evidence, not an approved price.',
            'recipe_eligibility': 'unconfirmed',
            'next_step': 'Calling agent reviews image and evidence, then applies the offline appraise skill.',
        },
        'timings_ms': {'retrieval': round((time.perf_counter() - started) * 1000, 2)},
    }


def extract_and_retrieve(image, database, **ocr_options):
    from pricing.knowledge.ocr import extract_image

    started = time.perf_counter()
    result = retrieve_draft(extract_image(image, **ocr_options), database)
    result['timings_ms']['image_to_evidence'] = round((time.perf_counter() - started) * 1000, 2)
    return result
