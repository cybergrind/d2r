import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('quality', ['normal', 'superior'])
def test_rhyme_preparation_requires_all_staffmods_and_empty_sockets(quality):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == 'mirrored-starter-rhyme-grimoire-base'
    ]
    assert len(configs) == 1
    keys = ('107:392', '107:389', '107:377')
    item = replace(facts('Grimoire', quality), sockets=2, stats={k: {'status': 'decoded', 'value': 1} for k in keys})

    def evaluate(candidate, context=None):
        context = {'player_class': 'Warlock'} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    result = evaluate(item)
    assert set(result.annotations) == set(keys)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    assert any('Shael then Eth' in s for s in result.configurations[0]['role']['missing'])
    for key in keys:
        for value in (0, None):
            assert not evaluate(
                replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value}})
            ).annotations
        absent = {k: v for k, v in item.stats.items() if k != key}
        assert not evaluate(replace(item, stats=absent, capture_complete=False)).annotations
    for wrong in ('107:404', '97:389', '83:7'):
        values = {k: v for k, v in item.stats.items() if k != '107:389'}
        values[wrong] = {'status': 'decoded', 'value': 3}
        assert not evaluate(replace(item, stats=values)).annotations
    for changes in (
        {'rarity': 'magic'},
        {'rarity': 'rare'},
        {'rarity': 'low_quality'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'base_code': facts('Monarch').base_code},
        {'socket_contents': 'filled'},
        {'socket_contents': 'partial'},
        {'socket_contents': None},
        {'sockets': 0},
        {'sockets': 1},
        {'sockets': 3},
        {'sockets': None},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(item, context).annotations
    assert set(evaluate(replace(item, stats={k: {'status': 'decoded', 'value': 3} for k in keys})).annotations) == set(
        keys
    )
