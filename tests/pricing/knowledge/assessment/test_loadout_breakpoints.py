from dataclasses import replace

import pytest

from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'context_at_least', 'field': 'player_total_fcr', 'value': 105}


def test_breakpoint_uses_explicit_loadout_total_not_hovered_item_stats():
    validate(RULE)
    item = replace(facts('Ring', 'rare'), stats={'105:0': {'status': 'decoded', 'value': 200}})
    assert evaluate(RULE, item, {}).truth == 'unknown'
    for total, expected in ((0, 'false'), (104, 'false'), (105, 'true'), (200, 'true')):
        result = evaluate(RULE, item, {'player_total_fcr': total})
        assert result.truth == expected
        assert result.observed == total
        assert result.expected == 105


def test_malformed_totals_stay_unknown():
    for total in (True, -1, '105', 105.0, float('inf'), None):
        context = AssessmentContext.from_input({'player_total_fcr': total})
        assert evaluate(RULE, facts('Ring'), context).truth == 'unknown'


@pytest.mark.parametrize(
    'rule',
    [
        {**RULE, 'field': 'player_class'},
        {**RULE, 'field': 'player_items'},
        {**RULE, 'value': True},
        {**RULE, 'value': -1},
        {**RULE, 'value': 105.0},
    ],
)
def test_breakpoint_schema_rejects_nonnumeric_fields_and_invalid_thresholds(rule):
    with pytest.raises(ValueError, match='Invalid numeric context threshold'):
        validate(rule)


def test_reviewed_whole_loadout_breakpoints_are_executable_across_builds():
    from pricing.knowledge.assessment.build_profiles import build

    expected = {
        'echoing-starter-dagger': 75,
        'lightning-mf-tal-armor': 117,
        'lightning-mf-tal-belt': 117,
        'lightning-mf-tal-amulet': 117,
        'abyss-starter-crafted-belt': 75,
        'echoing-starter-crafted-belt': 75,
        'lightning-starter-crafted-belt': 117,
        'nova-starter-crafted-belt': 105,
        'summoner-starter-crafted-belt': 75,
    }
    profiles = {p['id']: p for p in build()['profiles']}
    for identity, target in expected.items():
        dependency = next(
            (d for d in profiles[identity].get('depends_on', []) if d['when'].get('field') == 'player_total_fcr'), None
        )
        assert dependency is not None, identity
        assert dependency['when']['value'] == target
        assert evaluate(dependency['when'], facts('Ring'), {'player_total_fcr': target - 1}).truth == 'false'
        assert evaluate(dependency['when'], facts('Ring'), {'player_total_fcr': target}).truth == 'true'
