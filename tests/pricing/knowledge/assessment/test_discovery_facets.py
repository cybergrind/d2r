import json

import pytest

from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def database(tmp_path):
    source = tmp_path / 'rows.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    target = tmp_path / 'index.sqlite3'
    build_index([source], target)
    return target


def test_native_skill_discovery_uses_normalized_identity_not_display_text(tmp_path):
    item = facts('Ring', 'magic').to_dict()
    item['affixes'] = []
    extraction = {
        'item': item,
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {
                'memory_stat': {'id': 97, 'layer': 9, 'raw': 3},
                'status': 'decoded',
                'value': 3,
                'text': '+3 to Deliberately Different Display Label',
                'range_label': '+{{value}} to Deliberately Different Display Label',
            }
        ],
    }
    result = retrieve_draft(extraction, database(tmp_path))
    assert result['queries'][0]['facets']['properties'] == {'1210': 3}
    skill_queries = [q for q in result['queries'] if q['purpose'] == 'cross_base_skill_discovery']
    assert [q['facets'] for q in skill_queries] == [{'property_min': {'1210': 3}}]


def test_ocr_candidate_facets_remain_discovery_only(tmp_path):
    extraction = {
        'item': {
            'name': 'Ring',
            'rarity': 'magic',
            'affixes': [
                {'property_id': '442', 'value': 2, 'label': '+{{value}} to Paladin Skills (Paladin Only)'},
            ],
        }
    }
    result = retrieve_draft(extraction, database(tmp_path))
    assert result['queries'][0]['facets']['properties'] == {'442': 2}
    assert result['queries'][1]['facets'] == {'property_min': {'442': 2}}
    assert result['assessment']['contract'] is None
    assert result['price_estimate']['estimate_ist'] is None


def test_unresolved_native_skill_does_not_use_its_readable_label(tmp_path):
    item = facts('Ring', 'magic').to_dict()
    item['affixes'] = [
        {
            'property_id': '442',
            'value': 2,
            'label': '+{{value}} to Paladin Skill Levels',
            'memory_stat': {'id': 83, 'layer': 3, 'raw': 2},
        }
    ]
    extraction = {
        'item': item,
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {
                'memory_stat': {'id': 83, 'layer': 3, 'raw': 2},
                'status': 'unresolved',
                'value': 2,
                'text': '+2 to Paladin Skill Levels',
                'label': '+{{value}} to Paladin Skill Levels',
            }
        ],
    }
    result = retrieve_draft(extraction, database(tmp_path))
    assert 'properties' not in result['queries'][0]['facets']
    assert not any(q['purpose'] == 'cross_base_skill_discovery' for q in result['queries'])


@pytest.mark.parametrize(('prop', 'value'), [('858', 3), ('1210', 4)])
def test_conflicting_supplied_skill_projection_is_not_used_for_discovery(tmp_path, prop, value):
    from tests.pricing.knowledge.assessment.test_market_projection import extraction

    data = extraction(
        [(97, 9, 3, 3)],
        [
            {
                'property_id': prop,
                'value': value,
                'label': '+{{value}} to Critical Strike (Amazon Only)',
                'memory_stat': {'id': 97, 'layer': 9, 'raw': 3},
            }
        ],
    )
    result = retrieve_draft(data, database(tmp_path))
    assert 'properties' not in result['queries'][0]['facets']
    assert not any(q['purpose'] == 'cross_base_skill_discovery' for q in result['queries'])
    assert any('conflict' in gap.lower() for gap in result['assessment']['facts']['gaps'])
    assert result['extraction']['item']['affixes'][0]['property_id'] == prop
    assert result['price_estimate']['estimate_ist'] is None
