"""Image-to-local-evidence pipeline; the calling agent reviews and appraises the draft."""

import time
from datetime import UTC, date, datetime

from pricing.knowledge import definition_store
from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.adapters import discovery
from pricing.knowledge.assessment.adapters.priced import legacy_priced_payload
from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.guide_demand import demand_for_item
from pricing.knowledge.assessment.inputs import artifact_inputs
from pricing.knowledge.assessment.market_repository import compare_request_results, market_rows
from pricing.knowledge.assessment.pricing import finalize_assessment
from pricing.knowledge.bases import BASE_QUALITIES, assess_base
from pricing.knowledge.index import compact_result, lookup, search
from pricing.knowledge.snapshot import read_snapshot, verify_artifact_generation, verify_definition_generation


def retrieve_draft(extraction, database, *, loadout=None, as_of=None):
    """Retrieve candidate evidence without promoting OCR readings to verified facts."""
    if as_of is not None and type(as_of) is not date:
        raise ValueError('as_of must be a datetime.date')
    as_of = as_of or datetime.now(UTC).date()
    loadout = AssessmentContext.from_input(loadout)
    inputs = artifact_inputs()
    with (
        read_snapshot(database) as connection,
        definition_store.definition_snapshot() as definitions,
        artifact_snapshot(inputs) as artifacts,
    ):
        verify_definition_generation(connection, definitions, definition_store.STORE.path)
        for path, artifact in artifacts.items():
            verify_artifact_generation(connection, artifact.generation, path, inputs.get(path, 'artifact'))
        return _retrieve_draft(extraction, connection, loadout=loadout, as_of=as_of)


def _retrieve_draft(extraction, database, *, loadout, as_of):
    started = time.perf_counter()
    item = extraction['item']
    outcome = assess_result(extraction, loadout=loadout)
    facets = {
        key: item[key] for key in ('sockets', 'rarity', 'ethereal', 'socket_contents') if item.get(key) is not None
    }
    if item.get('runeword'):
        facets['rarity'] = 'runeword'
    properties = discovery.properties(outcome.facts)
    if properties:
        facets['properties'] = properties
    queries = []
    evidence = {}
    base_assessment = None
    if item.get('name'):
        name = item.get('base_name') if item.get('rarity') in ('magic', 'rare', 'crafted') else item['name']
        name = name or item['name']
        queries.append({'purpose': 'identity_candidates', 'name': name, 'facets': facets})
        is_base = item.get('rarity') in BASE_QUALITIES and not item.get('runeword')
        found = lookup(database, name, **facets, limit=1000 if is_base else 3)
        if is_base:
            base_assessment = assess_base(item, compact_result(found))
            found['evidence']['historical_market'] = base_assessment['historical_asks']
            found['evidence'] = {kind: rows[:3] for kind, rows in found['evidence'].items()}
        evidence['identity'] = compact_result(found)
    for property_id, value in discovery.skill_properties(outcome.facts, extraction).items():
        skill_facets = {'property_min': {property_id: value}}
        queries.append({'purpose': 'cross_base_skill_discovery', 'facets': skill_facets})
        evidence.setdefault('skills', []).append(compact_result(search(database, limit=3, **skill_facets)))
    query_name = (
        outcome.contract.name
        if outcome.contract
        else (item.get('base_name') if item.get('rarity') in ('magic', 'rare', 'crafted') else item.get('name'))
    )
    comparison_results = compare_request_results(database, outcome.comparison_requests, today=as_of)
    fallback_rows = (
        market_rows(database, query_name)
        if query_name and not any(result.is_current for result in comparison_results)
        else ()
    )
    priced = finalize_assessment(outcome, comparison_results, fallback_rows=fallback_rows, today=as_of)
    payload = legacy_priced_payload(priced)
    assessment, estimate = payload['assessment'], payload['price_estimate']
    watches = evidence.get('identity', {}).get('evidence', {}).get('value_watch', [])
    return {
        'price_estimate': estimate,
        'guide_demand': demand_for_item(item.get('runeword') or item.get('name'), assessment['roles']),
        'assessment': assessment,
        'value_watch': watches,
        'offline': True,
        'appraisal_ready': False,
        'extraction': extraction,
        'queries': queries,
        'evidence': evidence,
        **({'base_assessment': base_assessment} if base_assessment else {}),
        'decision': {
            'verdict': 'KEEP / REVIEW' if watches else 'REVIEW',
            'price_status': 'offline_ask_estimate'
            if estimate['estimate_ist'] is not None
            else base_assessment['price_status']
            if base_assessment
            else 'unresolved',
            'reason': 'Build suitability and trade value are separate; check the stated conditions and evidence gaps.',
            'recipe_eligibility': 'unconfirmed',
            'next_step': 'Check the reported setup conditions and missing comparison evidence.',
        },
        'timings_ms': {'retrieval': round((time.perf_counter() - started) * 1000, 2)},
    }


def extract_and_retrieve(image, database, *, loadout=None, as_of=None, **ocr_options):
    from pricing.knowledge.ocr import extract_image

    started = time.perf_counter()
    result = retrieve_draft(extract_image(image, **ocr_options), database, loadout=loadout, as_of=as_of)
    result['timings_ms']['image_to_evidence'] = round((time.perf_counter() - started) * 1000, 2)
    return result
