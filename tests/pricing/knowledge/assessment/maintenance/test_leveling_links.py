import json
from copy import deepcopy

from pricing.knowledge.assessment.build_profiles import ROOT
from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
from pricing.knowledge.assessment.maintenance.leveling_links import compile_leveling_links
from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs


def test_all_cached_patterns_link_exact_reviewed_policies_without_claiming_prices():
    recommendations = json.loads((ROOT / 'pricing/data/appraisal-recommendations.json').read_text())
    links = compile_leveling_links(recommendations)
    assert len(links) == 13
    assert len(next(r for r in links.values() if r['name'] == 'leveling rings')['policies']) == 2
    crushing = next(r for r in links.values() if r['name'] == 'crushing blow weapons')
    assert crushing['common_guards'] == {'identified': True}
    assert {(p['side'], p['ethereal_guard']) for p in crushing['policies']} == {
        ('player', False),
        ('mercenary', 'any'),
    }
    result = build_matrix(
        *inputs(), recommendations={'rows': [], 'patterns': recommendations['patterns']}, leveling_links=links
    )
    records = [r for r in result['rows'] if r['kind'] == 'evidence']
    assert len(records) == 13
    for row in records:
        assert row['policy_links']
        assert row['dimensions']['leveling']['state'] == 'reviewed'
        assert row['dimensions']['discovery']['state'] == 'reviewed'
        for key in ('market', 'stat_annotations', 'report'):
            assert row['dimensions'][key]['state'] == 'pending'
    assert result['counts']['unlinked_evidence'] == 0


def test_changed_pattern_context_does_not_inherit_reviewed_policy_link():
    recommendations = json.loads((ROOT / 'pricing/data/appraisal-recommendations.json').read_text())
    changed = deepcopy(recommendations)
    changed['patterns'][0]['context'] = 'All boots are valuable'
    links = compile_leveling_links(changed)
    assert len(links) == 12
    assert all(r['name'] != changed['patterns'][0]['name'] for r in links.values())


def test_foreign_or_changed_source_cannot_claim_policy_coverage(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge.assessment.policies import generic_leveling

    recommendations = json.loads((ROOT / 'pricing/data/appraisal-recommendations.json').read_text())
    changed = deepcopy(recommendations)
    for source in changed['sources']:
        source['url'] = 'https://example.invalid/unreviewed'
    assert not compile_leveling_links(changed)
    path = tmp_path / 'source.json'
    path.write_bytes(generic_leveling.SOURCE.read_bytes() + b'\n')
    monkeypatch.setattr(generic_leveling, 'SOURCE', path)
    with pytest.raises(ValueError, match='Stale'):
        compile_leveling_links(recommendations)
