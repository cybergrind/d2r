import json

import pytest

from pricing.knowledge.assessment.maintenance.rule_bundle import load_rule_bundle


def write_bundle(root):
    (root / 'roles').mkdir()
    (root / 'roles/a.json').write_text(json.dumps({'profiles': [{'id': 'a1'}, {'id': 'a2'}]}))
    (root / 'roles/b.json').write_text(json.dumps({'profiles': [{'id': 'b'}]}))
    manifest = {
        'schema_version': 1,
        'rules_version': 'assessment-1',
        'coverage': {},
        'profile_files': ['roles/a.json', 'roles/b.json'],
        'profile_order': ['a1', 'b', 'a2'],
    }
    path = root / 'manifest.json'
    path.write_text(json.dumps(manifest))
    return path, manifest


def test_bundle_preserves_published_order_and_does_not_expose_manifest_fields(tmp_path):
    path, manifest = write_bundle(tmp_path)
    result = load_rule_bundle(path)
    assert [p['id'] for p in result['profiles']] == ['a1', 'b', 'a2']
    assert 'profile_files' not in result
    assert result['coverage'] == manifest['coverage']


@pytest.mark.parametrize('order', [['a1', 'b'], ['a1', 'b', 'a2', 'missing'], ['a1', 'b', 'a1']])
def test_omitted_unknown_or_duplicate_profile_order_fails_publication(tmp_path, order):
    path, manifest = write_bundle(tmp_path)
    manifest['profile_order'] = order
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='order'):
        load_rule_bundle(path)


def test_bundle_rejects_duplicate_ids_and_files_outside_rules_root(tmp_path):
    path, manifest = write_bundle(tmp_path)
    (tmp_path / 'roles/b.json').write_text(json.dumps({'profiles': [{'id': 'a1'}]}))
    with pytest.raises(ValueError, match='Duplicate'):
        load_rule_bundle(path)
    manifest['profile_files'] = ['../outside.json']
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='outside'):
        load_rule_bundle(path)
