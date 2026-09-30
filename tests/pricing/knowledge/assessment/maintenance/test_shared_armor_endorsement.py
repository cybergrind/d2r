"""Shared armor review must not erase wearer or player-equipment dependencies."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.shared_armor_endorsement import shared_armor_role
from tests.pricing.knowledge.assessment.maintenance.test_armor_planner_links import read, shared_example


def proof():
    document, _, profiles, _ = shared_example()
    role = profiles[0]
    return document['rows'][0]['planner_endorsement'], role, read('pricing/data/wp-a-builds.json')[role['build']]


def validate(evidence, role, build):
    return shared_armor_role(evidence, role, build, lambda ref: read(ref['path']))


def test_shared_proof_retains_original_conditions_and_unknown_planner_flag():
    evidence, role, build = proof()
    original = deepcopy((evidence, role))
    result = validate(evidence, role, build)
    assert result['must']['all'][0] == role['must']
    assert result['must']['all'][1] == role['depends_on'][0]['when']
    assert result['conditions'] == role['conditions']
    assert result['depends_on'] == role['depends_on']
    assert (evidence, role) == original
    assert 'ethereal' not in evidence['expected_item']


@pytest.mark.parametrize(
    'change',
    [
        'missing-dependency',
        'optional-dependency',
        'wrong-dependency',
        'identified',
        'condition',
        'source-slot',
        'source-build',
        'source-quote',
        'variant',
        'recipe-pin',
        'base-label',
    ],
)
def test_shared_proof_rejects_missing_or_conflicting_requirements(change):
    evidence, role, build = proof()
    if change == 'missing-dependency':
        role['depends_on'] = []
    elif change == 'optional-dependency':
        role['depends_on'][0]['required'] = False
    elif change == 'wrong-dependency':
        role['depends_on'][0]['when']['value'] = 'Act 2 Prayer'
    elif change == 'identified':
        role['must']['all'].pop()
    elif change == 'condition':
        role['conditions'] = []
    elif change == 'source-slot':
        role['source']['locator'] = '/variants/1/player/Body Armor'
    elif change == 'source-build':
        role['source']['path'] = 'pricing/data/wp-a-variants/another-build.json'
    elif change == 'source-quote':
        role['source']['quotes'] = []
    elif change == 'variant':
        role['variant'] = 'Starter'
    elif change == 'recipe-pin':
        evidence['recipe_sources']['runes']['path'] = 'arbitrary.json'
    else:
        role['alternatives'] = ['Treachery in an unrelated base']
    with pytest.raises(ValueError, match='Shared armor'):
        validate(evidence, role, build)
