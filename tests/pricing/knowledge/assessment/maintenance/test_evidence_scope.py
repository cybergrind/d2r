"""Generic-leveling evidence exclusions cannot hide item or configuration work."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.evidence_scope import evidence_exclusions
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs
from tests.pricing.knowledge.assessment.maintenance.test_value_scope_manifest import POLICY


def sample(tmp_path):
    matrix, inventory = inputs()
    raw = {'name': 'early movement boots', 'context': 'Any early boots with faster run/walk.', 'slots': ['boots']}
    path = tmp_path / 'pricing/data/appraisal-leveling-candidates-2026-09-23.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'generic_patterns': [raw]}))
    row = {
        'id': 'evidence:recommendations:patterns:0',
        'kind': 'evidence',
        'evidence_kind': 'leveling_pattern',
        'name': raw['name'],
        'quality': None,
        'identity_ids': [],
        'candidate_identity_ids': [],
        'evidence': {**raw, 'source_id': 'mrllamasc-transcript', 'kind': 'recommendation_pattern', 'intent': 'pattern'},
        'source': {'artifact': 'recommendations', 'locator': '/patterns/0'},
        'dimensions': {},
    }
    matrix['rows'].append(row)
    review = {
        **deepcopy(POLICY),
        'evidence': [
            {
                'row_id': row['id'],
                'row_sha256': fingerprint(row),
                'classification': 'generic_leveling',
                'reason': 'Ordinary early movement fallback only; valuable boot identities and builds remain.',
                'reviewed_at': '2026-09-30',
                'quote': raw['context'],
                'source': {
                    'path': str(path.relative_to(tmp_path)),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'locator': '/generic_patterns/0',
                },
            }
        ],
    }
    return matrix, inventory, review, path


def test_exact_evidence_scope_does_not_remove_identity_or_source_work(tmp_path):
    matrix, inventory, review, _ = sample(tmp_path)
    sibling = deepcopy(matrix['rows'][-1])
    sibling['id'] = 'evidence:unreviewed-use'
    matrix['rows'].append(sibling)
    result = compile_completion(matrix, inventory, {}, value_scope=review, source_root=tmp_path)
    assert not any(r['id'].startswith('evidence:recommendations:patterns:0/') for r in result['queue'])
    assert 'occurrence:o' in {r['id'] for r in result['queue']}
    members = {r['id']: r for r in result['scope_manifest']['members']}
    assert members['evidence:recommendations:patterns:0']['state'] == 'excluded'
    assert members['identity:a']['state'] == members['occurrence:o']['state'] == 'retained'
    assert members['evidence:unreviewed-use']['state'] == 'retained'
    assert any(r['id'].startswith('evidence:unreviewed-use/') for r in result['queue'])
    assert len(result['evidence_scope_dispositions']) == 1
    assert not result['complete']


@pytest.mark.parametrize(
    'change', ['stale-row', 'stale-source', 'named-link', 'capture', 'quote', 'locator', 'duplicate']
)
def test_changed_or_incompatible_evidence_cannot_be_excluded(tmp_path, change):
    matrix, inventory, review, path = sample(tmp_path)
    row, entry = matrix['rows'][-1], review['evidence'][0]
    if change == 'stale-row':
        row['name'] = 'Changed'
    elif change == 'stale-source':
        path.write_text(path.read_text() + ' ')
    elif change == 'named-link':
        row['identity_ids'] = ['identity:a']
        entry['row_sha256'] = fingerprint(row)
    elif change == 'capture':
        row['kind'] = 'observed_capture'
        entry['row_sha256'] = fingerprint(row)
    elif change == 'quote':
        entry['quote'] = 'Invented'
    elif change == 'locator':
        entry['source']['locator'] = '/generic_patterns/00'
    else:
        review['evidence'].append(deepcopy(entry))
    with pytest.raises(ValueError, match='evidence scope'):
        compile_completion(matrix, inventory, {}, value_scope=review, source_root=tmp_path)


def test_ordinary_resistance_helm_does_not_remove_valuable_pattern_candidates():
    root = Path(__file__).resolve().parents[5]
    rows = json.loads((root / 'pricing/data/appraisal-coverage-matrix.json').read_text())['rows']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = evidence_exclusions(rows, review, root)
    assert excluded['evidence:recommendations:patterns:5']['state'] == 'excluded'
    # IAS affixes, caster crafts, named sockets and resistance charms need their
    # own value review; a generic helm recommendation cannot exclude them.
    retained = {f'evidence:recommendations:patterns:{index}' for index in (3, 4, 10, 12)}
    assert retained <= {row['id'] for row in rows}
    assert not retained.intersection(excluded)
    assert all(key.startswith('evidence:recommendations:patterns:') for key in excluded)
