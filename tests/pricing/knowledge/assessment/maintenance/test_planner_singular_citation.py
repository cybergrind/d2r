"""Older ledger citation spelling still requires the exact guide-selected planner."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.table_equivalence import _read


def example(profile_id):
    def read(path):
        return json.loads((ROOT / path).read_bytes())

    audit = read('pricing/data/appraisal-selected-armor-endorsement-audit.json')
    row = next(r for r in audit['rows'] if r['profile_id'] == profile_id)
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == profile_id)
    build = read('pricing/data/wp-a-builds.json')[role['build']]
    return {'planner_endorsement': deepcopy(row['planner_endorsement'])}, role, build


@pytest.mark.parametrize(
    'profile_id', ['echoing-strike-warlock-guide-1-player-enigma', 'dream-paladin-0-player-enigma']
)
def test_exact_singular_citation_preserves_full_recipe_validation(profile_id):
    review, role, build = example(profile_id)
    validate_endorsement(review, role, build, ROOT, lambda ref: json.loads(_read(ROOT, ref)))


@pytest.mark.parametrize(
    'citation',
    [
        'unrelated (Other guide)',
        'ucgz20lex (Other guide)',
        'mentioned ucgz20le (Other guide)',
        'ucgz20le',
        'ucgz20le (Guide) unrelated',
    ],
)
def test_singular_citation_requires_exact_identifier_and_format(citation):
    review, role, build = example('echoing-strike-warlock-guide-1-player-enigma')
    build['variants_sources']['planner_profile'] = citation
    with pytest.raises(ValueError, match='not a cited source'):
        validate_endorsement(review, role, build, ROOT, lambda ref: json.loads(_read(ROOT, ref)))
