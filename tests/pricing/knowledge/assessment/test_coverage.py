import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.coverage import audit_named


def test_named_audit_keeps_unreviewed_items_and_cached_research_distinct(tmp_path):
    evidence = {'record': {'name': 'Reviewed', 'type': 'set'}, 'other': {'name': 'Research only', 'type': 'unique'}}
    source = tmp_path / 'source.json'
    source.write_text(json.dumps(evidence))
    definitions = {
        ('set', 'Reviewed'): {'base_codes': ['verified']},
        ('unique', 'Research only'): {'base_codes': ['verified']},
        ('unique', 'Missing'): {'base_codes': ['verified']},
    }
    policies = {
        ('set', 'Reviewed'): {
            'default_tier': 'low',
            'source': {
                'path': 'source.json',
                'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'locator': '/record',
                'date': '2026-09-18',
            },
        }
    }
    report = audit_named(definitions, policies, evidence, tmp_path)
    assert report['counts'] == {
        'identities': 3,
        'reviewed_policies': 1,
        'research_only': 1,
        'missing_research': 1,
        'invalid_sources': 0,
    }
    assert report['identity_policy_complete'] is False
    assert [r['name'] for r in report['rows']] == ['Reviewed', 'Missing', 'Research only']
    assert report['rows'][1]['tier'] is None
    assert report['rows'][2]['status'] == 'research_only'
    source.write_text('{}')
    stale = audit_named(definitions, policies, evidence, tmp_path)
    assert stale['counts']['invalid_sources'] == 1
    assert stale['counts']['reviewed_policies'] == 0


def test_named_audit_rejects_orphan_policy_and_escaped_sources(tmp_path):
    with pytest.raises(ValueError, match='Unknown policy identities'):
        audit_named({}, {('unique', 'Ghost'): {}}, {}, tmp_path)
    defs = {('set', 'Known'): {'base_codes': []}}
    policy = {
        ('set', 'Known'): {
            'default_tier': 'low',
            'source': {'path': '../outside.json', 'sha256': 'unknown', 'locator': '/record'},
        }
    }
    result = audit_named(defs, policy, {}, tmp_path)
    assert result['rows'][0]['status'] == 'invalid_source'
    assert 'outside' in result['rows'][0]['source_error']


def test_spawnability_audit_keeps_disabled_legacy_variants_and_unverified_new_definitions(tmp_path):
    definitions = {('unique', name): {'base_codes': ['base']} for name in ('Both', 'Disabled', 'Unverified')}
    variants = {
        ('unique', 'Both'): [
            {'table_id': 1, 'base_codes': ['legacy'], 'game_definition': {'spawnable': 0}},
            {'table_id': 2, 'base_codes': ['current'], 'game_definition': {'spawnable': 1}},
        ],
        ('unique', 'Disabled'): [{'table_id': 3, 'base_codes': ['base'], 'game_definition': {'spawnable': 0}}],
        ('unique', 'Unverified'): [{'table_id': 4, 'base_codes': ['base'], 'game_definition': {}}],
    }
    result = audit_named(definitions, {}, {}, tmp_path, variants=variants)
    rows = {r['name']: r for r in result['rows']}
    assert rows['Both']['spawnability'] == 'enabled'
    assert [v['spawnability'] for v in rows['Both']['definition_variants']] == ['disabled', 'enabled']
    assert rows['Disabled']['spawnability'] == 'disabled'
    assert rows['Unverified']['spawnability'] == 'unverified'
    assert result['definition_counts'] == {'total': 4, 'enabled': 1, 'disabled': 2, 'unverified': 1}
    # Disabled drop definitions still remain explicit identities for review, not automatic trash.
    assert result['counts']['missing_research'] == 3
    assert all(r['tier'] is None for r in result['rows'])
