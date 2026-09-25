import json
from datetime import date

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft


def database(tmp_path, rows=()):
    path = tmp_path / 'rows.json'
    path.write_text(json.dumps({'schema_version': 1, 'rows': list(rows)}))
    output = tmp_path / 'kb.sqlite3'
    build_index([path], output)
    return output


def test_pipeline_explicit_date_controls_freshness_of_the_same_offline_cohort(tmp_path):
    rows = [
        {
            'kind': 'market',
            'name': 'Cinquedeas',
            'base_code': next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Cinquedeas'),
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 3,
            'socket_contents': 'empty',
            'properties': {},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': i,
            'observed_at': '2026-09-24',
        }
        for i in (1, 2, 3)
    ]
    db = database(tmp_path, rows)
    item = {
        'item': {
            **{k: rows[0][k] for k in ('name', 'rarity', 'ethereal', 'sockets', 'socket_contents')},
            'base_name': 'Cinquedeas',
            'base_code': next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Cinquedeas'),
            'identified': True,
            'affixes': [],
        },
        'decoded_stats': [],
        'source': {'stat_capture_complete': True},
    }
    fresh = retrieve_draft(item, db, as_of=date(2026, 9, 24))
    stale = retrieve_draft(item, db, as_of=date(2026, 10, 25))
    assert fresh['price_estimate']['estimate_ist'] == 2
    assert stale['price_estimate']['estimate_ist'] is None
    assert stale['price_estimate']['excluded_observations'] == {'stale': 3}
    assert fresh['assessment']['comparisons']['accepted'] == stale['assessment']['comparisons']['accepted']
    assert stale['assessment']['comparison_results'][0]['price_estimate']['publication_policy']['as_of'] == '2026-10-25'


def test_known_mercenary_loadout_resolves_only_satisfied_sazabi_conditions(tmp_path):
    extraction = replay('sazabi_mental_sheath')['extraction']
    db = database(tmp_path)
    unknown = retrieve_draft(extraction, db)
    known = retrieve_draft(
        extraction,
        db,
        loadout={
            'mercenary_type': 'Act 5 Frenzy',
            'mercenary_items': ["Sazabi's Cobalt Redeemer", "Sazabi's Ghost Liberator"],
        },
    )

    def select(result):
        return next(r for r in result['assessment']['roles'] if r['id'] == 'echoing-ubers-sazabi-helm')

    before, after = select(unknown), select(known)
    assert any('Set companions not confirmed' in s for s in before['missing'])
    assert not any('Set companions not confirmed' in s or 'Mercenary type not confirmed' in s for s in after['missing'])
    assert after['status'] == 'partial'  # Cham and the remaining setup still need verification.
    assert after['missing']
    assert unknown['assessment']['contract'] == known['assessment']['contract']


def test_invalid_assessment_date_is_rejected_before_retrieval(tmp_path):
    with pytest.raises(ValueError, match='as_of'):
        retrieve_draft({}, tmp_path / 'missing.sqlite3', as_of='2026-09-24')


def test_image_entry_keeps_assessment_options_out_of_ocr(tmp_path, monkeypatch):
    from pricing.knowledge import ocr
    from pricing.knowledge.pipeline import extract_and_retrieve

    def extract(image, **options):
        assert image == 'fixture.png'
        assert options == {'language': 'eng'}
        return {'item': {'name': 'Unknown item', 'affixes': []}}

    monkeypatch.setattr(ocr, 'extract_image', extract)
    result = extract_and_retrieve(
        'fixture.png', database(tmp_path), as_of=date(2026, 9, 24), loadout={'player_class': 'Warlock'}, language='eng'
    )
    assert result['price_estimate']['publication_policy']['as_of'] == '2026-09-24'
    assert result['price_estimate']['estimate_ist'] is None
    assert 'image_to_evidence' in result['timings_ms']
