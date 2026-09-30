import hashlib
import json

from pricing.knowledge.assessment.maintenance.reviewed_source_issues import reviewed_source_issues


def test_reviewed_issue_requires_exact_source_and_mechanics_snapshots(tmp_path):
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'build': {'amulet': ['Magic +skills / res / MF']}}))
    mechanics = tmp_path / 'prefix.json'
    mechanics.write_text('{}')
    row = {
        'id': 'two-prefixes',
        'reason': 'magic_prefix_conflict',
        'source': {
            'path': 'source.json',
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'locator': '/build/amulet',
            'expected': ['Magic +skills / res / MF'],
        },
        'mechanics': [{'path': 'prefix.json', 'sha256': hashlib.sha256(mechanics.read_bytes()).hexdigest()}],
        'review': 'Two prefixes cannot be used on one ordinary magic item.',
    }
    result = reviewed_source_issues([row], tmp_path)
    assert result[0]['status'] == 'reviewed_conflict'
    assert result[0]['source']['expected'] == row['source']['expected']
    wrong_locator = {**row, 'source': {**row['source'], 'locator': '/build/missing'}}
    assert reviewed_source_issues([wrong_locator], tmp_path)[0]['status'] == 'stale_review'
    wrong_value = {**row, 'source': {**row['source'], 'expected': ['different']}}
    assert reviewed_source_issues([wrong_value], tmp_path)[0]['status'] == 'stale_review'
    source.write_text(json.dumps({'build': {'amulet': ['Rare amulet']}}))
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    source.write_text(json.dumps({'build': {'amulet': ['Magic +skills / res / MF']}}))
    mechanics.write_text('{"changed": true}')
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    mechanics.unlink()
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    assert row.get('status') is None


def test_reconciliation_requires_pinned_planner_item_and_profile_link(tmp_path):
    planner = {
        'items': {'34': {'quality': 4, 'name': 'Wraith Collar'}},
        'profiles': [{'uid': 'starter', 'items': {'neck': 34}}],
    }
    path = tmp_path / 'planner.json'
    path.write_text(json.dumps({'data': json.dumps({'planner': planner})}))
    source = tmp_path / 'source.json'
    source.write_text('["Magic Amulet"]')

    def reference(locator, expected):
        return {
            'path': 'planner.json',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'format': 'maxroll_planner',
            'locator': locator,
            'expected': expected,
        }

    row = {
        'id': 'amulet',
        'source': {'path': 'source.json', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
        'mechanics': [],
        'resolution': {
            'corrected_rarity': 'rare',
            'evidence': [reference('/items/34', planner['items']['34']), reference('/profiles/0/items/neck', 34)],
        },
    }
    result = reviewed_source_issues([row], tmp_path)[0]
    assert result['status'] == 'reconciled_source'
    assert result['resolution']['corrected_rarity'] == 'rare'
    # Same file/hash but wrong profile link must not validate a correction.
    row['resolution']['evidence'][1]['expected'] = 35
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    row['resolution']['evidence'][1]['expected'] = 34
    path.write_text('{}')
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    row['resolution']['evidence'] = []
    assert reviewed_source_issues([row], tmp_path)[0]['status'] == 'stale_review'
    assert 'status' not in row
