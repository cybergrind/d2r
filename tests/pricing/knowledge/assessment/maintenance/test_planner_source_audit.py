import hashlib
import json

from pricing.knowledge.assessment.maintenance.planner_source_audit import audit_sources


def source(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value) if not isinstance(value, str) else value).encode()
    path.write_bytes(raw)
    return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest()}


def test_cross_guide_reference_preserves_dormant_definition(tmp_path):
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'items': {'1': {}, '2': {}}, 'profiles': []})
    guide = source(tmp_path, 'other.html', '<a data-d2planner-profile="a" data-d2planner-id="1">x</a>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    assert result['planner_reports'][planner['path']]['reachable'] == ['1']
    assert result['planner_reports'][planner['path']]['unreachable_candidates'] == ['2']
    assert result['exclusions_approved'] is False


def test_source_drift_blocks_candidate_output(tmp_path):
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'items': {'1': {}}, 'profiles': []})
    guide = source(tmp_path, 'other.html', '<p>old</p>')
    (tmp_path / 'other.html').write_text('<p>changed</p>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    assert result['source_issues']
    assert result['planner_reports'][planner['path']]['unreachable_candidates'] == []


def test_missing_planner_response_stays_an_explicit_gap(tmp_path):
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'error': 'Profile not found'})
    guide = source(tmp_path, 'other.html', '<span data-d2planner-profile="a" data-d2planner-id="1">x</span>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    assert result['missing_planners'] == ['a']
    assert result['unsupported_sources'][0]['source'] == planner['path']
    assert result['guide_reference_sources']['a'] == [{'source': 'other.html', 'item_ids': ['1']}]


def test_unknown_guide_item_blocks_candidate_output(tmp_path):
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'items': {'1': {}}, 'profiles': []})
    guide = source(tmp_path, 'other.html', '<span data-d2planner-id="1">x</span>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    assert result['guide_issues']
    assert result['planner_reports'][planner['path']]['unreachable_candidates'] == []


def test_modern_definition_only_reference_protects_item_and_socket_children(tmp_path):
    planner = source(
        tmp_path,
        'pricing/raw/mr/planners/a.json',
        {
            'items': {'143': {'socketedItems': ['135', 'r24']}, '135': {}, '999': {}},
            'profiles': [],
        },
    )
    guide = source(tmp_path, 'other.html', '<span data-d2-id="a" data-d2-set-id="embeds" data-d2-item-id="143"></span>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    report = result['planner_reports'][planner['path']]
    assert report['reachable'] == ['135', '143']
    assert report['unreachable_candidates'] == ['999']
    assert result['guide_reference_sources']['a'] == [{'source': 'other.html', 'item_ids': ['143']}]
    assert result['exclusions_approved'] is False


def test_missing_planner_stays_a_gap_without_hiding_other_planners(tmp_path):
    # Guide references are keyed by planner id: a missing planner cannot root another planner's items.
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'items': {'1': {}}, 'profiles': []})
    guide = source(tmp_path, 'other.html', '<span data-d2-id="missing" data-d2-item-id="143"></span>')
    result = audit_sources({'sources': [planner, guide]}, tmp_path, catalog_ids=())
    assert result['missing_planners'] == ['missing']
    assert result['planner_reports'][planner['path']]['unreachable_candidates'] == ['1']


def test_unsupported_planner_does_not_block_other_planners(tmp_path):
    broken = source(tmp_path, 'pricing/raw/mr/planners/b.json', {'error': 'Profile not found'})
    planner = source(tmp_path, 'pricing/raw/mr/planners/a.json', {'items': {'1': {}, '2': {}}, 'profiles': []})
    guide = source(tmp_path, 'other.html', '<a data-d2planner-profile="a" data-d2planner-id="1">x</a>')
    result = audit_sources({'sources': [broken, planner, guide]}, tmp_path, catalog_ids=())
    assert result['unsupported_sources'][0]['source'] == broken['path']
    assert result['planner_reports'][planner['path']]['unreachable_candidates'] == ['2']
