import json
from datetime import date

import pytest

from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_comparables import listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def priced_ring():
    item = facts('Ring', 'rare', 'Generated Rare Name').to_dict()
    stat = {'id': 105, 'layer': 0, 'raw': 10}
    item['affixes'] = [
        {'property_id': '520', 'value': 10, 'memory_stat': stat, 'label': '+{{value}}% Faster Cast Rate'}
    ]
    extraction = {
        'item': item,
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {'memory_stat': stat, 'status': 'decoded', 'value': 10, 'text': '+10% Faster Cast Rate'},
        ],
    }
    rows = [
        listing(
            str(i),
            kind='market',
            name='Ring',
            rarity='rare',
            base_code=item['base_code'],
            sockets=0,
            properties={'520': 10},
            ask_ist=i,
        )
        for i in (1, 2, 3)
    ]
    return extraction, rows


def retrieve(tmp_path, extraction, rows):
    source = tmp_path / 'rows.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    return retrieve_draft(extraction, database, as_of=date(2026, 9, 25))


def test_complete_exact_cohort_reaches_the_real_pipeline_price(tmp_path):
    extraction, rows = priced_ring()
    result = retrieve(tmp_path, extraction, rows)
    assert result['assessment']['contract'] is not None
    assert result['price_estimate']['estimate_ist'] == 2
    assert result['price_estimate']['sellers'] == 3


@pytest.mark.parametrize('case', ['name_only', 'facet_summary', 'undecoded'])
def test_context_or_incomplete_capture_cannot_bypass_the_real_contract(tmp_path, case):
    extraction, rows = priced_ring()
    if case == 'name_only':
        rows = [{**r, 'properties': {}} for r in rows]
    elif case == 'facet_summary':
        rows = [
            {
                'kind': 'market',
                'name': 'Ring',
                'rarity': 'rare',
                'properties': {'520': 10},
                'scope_status': 'verified',
                'band_kind': 'facet_matched',
                'priced_sellers': 3,
                'median_ist': 97,
                'min_ist': 90,
                'max_ist': 100,
                'observed_dates': ['2026-09-24'],
            }
        ]
    else:
        # Actual exact seller evidence is present, but a native modifier is unreadable.
        extraction['decoded_stats'].append(
            {'memory_stat': {'id': 999, 'layer': 0, 'raw': 1}, 'status': 'unresolved', 'text': 'Unknown modifier'}
        )
        extraction['unresolved_stats'] = [{'id': 999, 'layer': 0, 'raw': 1}]
    result = retrieve(tmp_path, extraction, rows)
    assert result['price_estimate']['estimate_ist'] is None
    assert result['price_estimate']['confidence'] == 'insufficient'
    assert not result['assessment']['comparisons']['accepted']
    if case == 'undecoded':
        assert result['assessment']['contract'] is None
