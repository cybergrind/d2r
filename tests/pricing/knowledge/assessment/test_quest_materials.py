"""Actual saved materials must reach reviewed utility and exact comparison handling."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.engine import assess


FIXTURE = json.loads((Path(__file__).parent / 'fixtures/quest_materials.json').read_text())['rows']


@pytest.mark.parametrize('row', FIXTURE, ids=lambda row: row['observation']['item']['base_name'])
def test_saved_recipe_material_has_specific_utility_and_comparison(row):
    result = assess(row['observation'], profiles=[])
    assert result['family'] == 'quest_material'
    assert result['utility']['status'] == 'usable'
    assert result['utility']['uses']
    if row['observation']['item']['base_name'] == 'Horadric Cube':
        assert result['contract'] is None
        assert result['utility']['kind'] == 'quest_utility'
    else:
        assert result['contract']['policy'] == 'quest_material', result['price_gaps']
        assert result['contract']['properties'] == {}
        assert result['contract']['base_code'] == row['observation']['item']['base_code']


@pytest.mark.parametrize(
    'change',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'rarity': 'magic'},
        {'complete': False},
        {'raw_stats': ((70, 0, 2),)},
        {'raw_stats': ((39, 0, 20),)},
    ],
)
def test_material_unknown_or_impossible_facets_do_not_form_a_contract(change):
    from dataclasses import replace

    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = replace(Item('Key of Terror', 'normal', complete=True), **change)
    result = assess(item.capture(), profiles=[])
    assert result['contract'] is None
    assert result['utility']['status'] == 'review'


def test_localized_material_names_and_token_instruction_match_pinned_strings():
    import hashlib

    from pricing.knowledge.assessment.policies.quest_materials import NAMES, ROOT, STRINGS_SHA256, STRINGS_SOURCE

    raw = (ROOT / STRINGS_SOURCE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == STRINGS_SHA256
    strings = json.loads(raw)
    for code, name in NAMES.items():
        assert strings[code] == name
    assert strings['UseTokenOfAbsolution'] == 'Right Click to reset Stat/Skill Points'


def test_shared_quest_type_does_not_grant_unreviewed_items_trade_contracts():
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    for name in ('Book of Skill', 'Standard of Heroes', "Mephisto's Soulstone"):
        result = assess(Item(name, 'normal', complete=True).capture(), profiles=[])
        assert result['contract'] is None
        assert result.get('utility') is None


@pytest.fixture(scope='module')
def published():
    from pricing.knowledge.publication import current_generation
    from pricing.knowledge.published_runtime import load_runtime

    return load_runtime(current_generation('pricing/data/generations'))


@pytest.mark.parametrize('row', FIXTURE, ids=lambda row: row['observation']['item']['base_name'])
def test_saved_material_renders_under_strict_published_snapshot(published, row):
    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.pipeline import retrieve_draft
    from pricing.knowledge.published_runtime import published_snapshot

    with published_snapshot(published):
        result = retrieve_draft(row['observation'], published.database)
        report = format_appraisal({'state': 'complete', 'request_id': 'material', 'result': result})
    cube = row['observation']['item']['base_name'] == 'Horadric Cube'
    assert ('Quest utility:' if cube else 'Use:') in report
    assert result['assessment']['utility']['name'] in report
    assert 'unsupported comparison policy' not in report
    assert 'No supported stats decoded' not in report
