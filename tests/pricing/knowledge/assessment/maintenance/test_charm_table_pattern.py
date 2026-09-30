"""Raw guide and planner must both prove the reviewed magic charm combination."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
ROLE = 'double-throw-sharp-dexterity-grand-charm'


def read(path):
    return json.loads((ROOT / path).read_text())


def pin(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


@pytest.fixture(scope='module')
def evidence():
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    occurrence = next(
        o
        for o in occurrences
        if o['source_id'] == 'pricing/raw/mr/guides__double-throw-barbarian-guide.html'
        and o['source_locator'] == '/item-spans/200'
    )
    role = next(p for p in profiles if p['id'] == ROLE)
    use = next(u for u in uses if u['profile_id'] == ROLE)
    review = {
        'occurrence_id': occurrence['id'],
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': ROLE,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-10-01',
        'reason': 'Guide entry200 and planner item140 corroborate the Sharp/Dexterity charm combination.',
        'pattern_kind': 'double_throw_sharp_dexterity_charm',
        'pattern_label': 'Sharp Grand Charm of Dexterity',
        'guide': pin('pricing/raw/mr/guides__double-throw-barbarian-guide.html'),
        'cache': pin('pricing/data/appraisal-guide-sections.json'),
        'planner': pin('pricing/raw/mr/planners/db0106mf.json'),
        'prefixes': pin('third-parties/d2data/json/magicprefix.json'),
        'suffixes': pin('third-parties/d2data/json/magicsuffix.json'),
    }
    return review, occurrences, profiles, uses


def test_sharp_dexterity_charm_binds_the_exact_raw_table_occurrence(evidence):
    review, occurrences, profiles, uses = evidence
    result = compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)
    assert [(r['occurrence_id'], r['profile_id'], r['state']) for r in result] == [
        (review['occurrence_id'], ROLE, 'reviewed'),
    ]


@pytest.mark.parametrize('mutation', ['label', 'planner', 'prefixes', 'suffixes'])
def test_sharp_dexterity_charm_rejects_mismatched_witnesses(evidence, mutation):
    original, occurrences, profiles, uses = evidence
    review = deepcopy(original)
    if mutation == 'label':
        review['pattern_label'] = 'Sharp Grand Charm of Vita'
    else:
        review[mutation] = pin('third-parties/d2data/json/uniqueitems.json')
    with pytest.raises(ValueError, match='endorsement' if mutation == 'label' else 'native witnesses'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)
