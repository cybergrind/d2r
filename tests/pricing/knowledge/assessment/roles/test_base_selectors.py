from dataclasses import replace

import pytest

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_roles, validate_profiles
from pricing.knowledge.assessment.roles.candidates import CandidateIndex
from pricing.knowledge.assessment.roles.predicates import evaluate
from pricing.knowledge.assessment.stat_bundle import configuration_from_row, configuration_row
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def specific_role():
    return {
        'id': 'specific',
        'build': 'abyss-warlock-build-guide',
        'variant': 'Main alternatives',
        'side': 'player',
        'slot': 'Weapon',
        'role': 'Specific base caster use',
        'review_status': 'reviewed_candidate_rule',
        'qualities': ['rare'],
        'types': ['knif'],
        'base_codes': [facts('Kriss').base_code],
        'must': {'op': 'stat_at_least', 'key': '83:7', 'value': 2},
        'conditions': [],
        'source': {'path': 'fixture', 'sha256': 'fixture', 'locator': '/role'},
    }


def test_known_wrong_base_is_excluded_but_unknown_base_stays_conditional():
    role = specific_role()
    validate_profiles([role])
    index = CandidateIndex([role])
    right = replace(facts('Kriss', 'rare'), stats={'83:7': {'status': 'decoded', 'value': 2}})
    wrong = replace(right, base_code=facts('Cinquedeas').base_code)
    assert index.select(right) == [role]
    assert not index.select(wrong)
    assert not assess_roles(wrong, [role])
    unknown = replace(right, base_code=None)
    assert index.select(unknown) == [role]
    result = assess_roles(unknown, [role])[0]
    assert result['status'] == 'partial'
    assert 'Role selector base_codes is unknown.' in result['missing']


def test_detached_stat_gate_binds_base_selector_without_a_base_predicate():
    role = specific_role()
    review = {
        'id': 'stats',
        'version': 1,
        'role_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'review_date': '2026-09-26',
        'review_state': 'reviewed',
        'rationale': 'Specific base caster skill',
        'priorities': [
            {
                'key': '83:7',
                'desirability': 'desirable',
                'activation': role['must'],
                'explanation': 'Required class skills',
            }
        ],
    }
    (config,) = compile_stat_configurations([review], [role])
    config = configuration_from_row(configuration_row(config))
    item = replace(facts('Kriss', 'rare'), stats={'83:7': {'status': 'decoded', 'value': 2}})
    assert evaluate(thaw(config.required), item).truth == 'true'
    assert evaluate(thaw(config.required), replace(item, base_code=facts('Cinquedeas').base_code)).truth == 'false'
    assert evaluate(thaw(config.required), replace(item, base_code=None)).truth == 'unknown'


@pytest.mark.parametrize('codes', [[], None, 'not-a-list', ['not-native'], [None], ['duplicate', 'duplicate']])
def test_invalid_native_base_selectors_fail_validation(codes):
    with pytest.raises(ValueError, match='base selectors'):
        validate_profiles([{**specific_role(), 'base_codes': codes}])
