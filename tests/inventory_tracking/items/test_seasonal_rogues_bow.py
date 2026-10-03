from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.seasonal_identity import resolve_seasonal_identity
from pricing.knowledge.seasonal_variants import select_scalar_candidates


@pytest.fixture
def row():
    return deepcopy(metadata()['identities']['unique']['62'])


def capture(stats, complete=True):
    return {'complete': complete, 'arrays': [{'header_offset': 0xE8, 'stats': stats}]}


@pytest.mark.parametrize('skill', [7, 11])
@pytest.mark.parametrize('value', [1, 2, 3])
def test_recognizes_each_seasonal_skill_roll(row, skill, value):
    stats = {f'107:{skill}': {'status': 'decoded', 'value': value}}
    assert select_scalar_candidates([row, row['ladder_definition']], stats) == [row['ladder_definition']]
    actual = resolve_seasonal_identity(row, capture([{'id': 107, 'layer': skill, 'raw': value}]), socketed=False)
    assert actual['mode_eligibility'] == 'ladder_only'


def test_complete_absence_selects_ordinary(row):
    assert select_scalar_candidates([row, row['ladder_definition']], {}) == [row]


@pytest.mark.parametrize(
    'stats',
    [
        {'107:7': {'status': 'decoded', 'value': 4}},
        {'107:11': {'status': 'decoded', 'value': -1}},
        {'107:7': {'status': 'decoded', 'value': 1.5}},
        {'107:7': {'status': 'decoded', 'value': 1}, '107:11': {'status': 'decoded', 'value': 1}},
    ],
)
def test_conflicting_skill_combinations_select_neither(row, stats):
    assert select_scalar_candidates([row, row['ladder_definition']], stats) == []


@pytest.mark.parametrize(('complete', 'socketed'), [(False, False), (True, True)])
def test_incomplete_or_socketed_stats_do_not_establish_ladder_version(row, complete, socketed):
    actual = resolve_seasonal_identity(row, capture([{'id': 107, 'layer': 7, 'raw': 3}], complete), socketed=socketed)
    assert actual['definition_variant'] == 'ordinary'
    assert 'mode_eligibility' not in actual


def test_duplicate_skill_capture_does_not_establish_version(row):
    stat = {'id': 107, 'layer': 7, 'raw': 2}
    actual = resolve_seasonal_identity(row, capture([stat, stat]), socketed=False)
    assert 'mode_eligibility' not in actual


def test_unknown_skill_decoding_retains_both_candidates(row):
    variants = [row, row['ladder_definition']]
    assert select_scalar_candidates(variants, {'107:7': {'status': 'unresolved', 'value': 2}}) == variants


def test_reviewed_skill_ids_match_native_metadata():
    assert metadata()['skills']['7']['name'] == 'Fire Arrow'
    assert metadata()['skills']['11']['name'] == 'Cold Arrow'


@pytest.mark.parametrize('skill', [7, 11])
def test_published_report_rejects_seasonal_rogues_bow(monkeypatch, skill):
    from datetime import date

    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.pipeline import retrieve_draft
    from pricing.knowledge.publication import current_generation
    from pricing.knowledge.published_runtime import load_runtime, published_snapshot
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    monkeypatch.setattr('inventory_tracking.items.identity.resolve_seasonal_identity', resolve_seasonal_identity)
    monkeypatch.setattr(
        'pricing.knowledge.assessment.handlers.seasonal.select_scalar_candidates', select_scalar_candidates
    )
    item = Item(
        'Composite Bow',
        'unique',
        "Rogue's Bow",
        (
            (39, 0, 10),
            (41, 0, 10),
            (43, 0, 10),
            (45, 0, 10),
            (141, 0, 30),
            (19, 0, 60),
            (122, 0, 100),
            (17, 0, 50),
            (18, 0, 50),
            (93, 0, 50),
            (107, skill, 3),
        ),
        complete=True,
    )
    runtime = load_runtime(current_generation('pricing/data/generations'))
    with published_snapshot(runtime):
        result = retrieve_draft(item.capture(), runtime.database, loadout={}, as_of=date(2026, 10, 3))
        text = format_appraisal({'state': 'complete', 'request_id': 'seasonal-bow', 'result': result})
    assert result['extraction']['source']['item_identity']['mode_eligibility'] == 'ladder_only'
    assert result['assessment']['contract'] is None
    assert result['assessment']['trade_tier']['status'] == 'out_of_scope'
    assert result['assessment']['roles'] == []
    assert result['price_estimate']['estimate_ist'] is None
    assert ('Fire Arrow' if skill == 7 else 'Cold Arrow') in text


def test_changed_group_or_other_identity_does_not_borrow_review(row):
    variants = [row, row['ladder_definition']]
    stats = {'107:7': {'status': 'decoded', 'value': 2}}
    variants[1]['property_groups'][0]['game_definition']['ModMax1'] = 4
    assert select_scalar_candidates(variants, stats) == variants
    variants[1]['table_id'] = 63
    assert select_scalar_candidates(variants, stats) == variants
