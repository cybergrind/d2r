from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('berserk-barbarian', 'Barbarian', 'Bone Shield', {}),
    ('blessed-hammer-paladin', 'Paladin', 'Targe', {}),
    ('blizzard-sorceress', 'Sorceress', 'Bone Shield', {}),
    ('echoing-strike-warlock-guide', 'Warlock', 'Codex', {'107:389': 1, '107:381': 1, '107:377': 1}),
    ('fire-blast-assassin', 'Assassin', 'Bone Shield', {}),
    ('fire-warlock-guide', 'Warlock', 'Codex', {}),
    ('lightning-fury-amazon-guide', 'Amazon', 'Bone Shield', {}),
    ('lightning-sentry-assassin', 'Assassin', 'Bone Shield', {}),
    ('lightning-sorceress', 'Sorceress', 'Bone Shield', {}),
    ('lightning-strike-amazon', 'Amazon', 'Bone Shield', {}),
    ('meteor-sorceress', 'Sorceress', 'Bone Shield', {}),
    ('poison-nova-necromancer', 'Necromancer', 'Fetish Trophy', {'107:92': 2}),
    ('smite-paladin', 'Paladin', 'Targe', {}),
    ('wake-of-fire-assassin', 'Assassin', 'Bone Shield', {}),
    ('mirrored-blades-warlock-guide', 'Warlock', 'Grimoire', {'107:392': 1, '107:389': 1, '107:377': 1}),
]


@pytest.mark.parametrize(('slug', 'cls', 'base', 'skills'), MEMBERS)
def test_rhyme_starter_roles_keep_recipe_staffmods_and_swap_scope(slug, cls, base, skills):
    b = build()
    rid = 'mirrored-starter-rhyme-grimoire' if slug == 'mirrored-blades-warlock-guide' else slug + '-0-rhyme'
    r = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert r is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {
        '153:0': 1,
        '80:0': 25,
        '102:0': 40,
        '20:0': 20,
        **dict.fromkeys(['39:0', '41:0', '43:0', '45:0'], 25),
        **skills,
    }
    item = replace(
        facts(base, name='Rhyme'),
        runeword='Rhyme',
        sockets=2,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls}

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [r], ctx)
        )

    assert set(evaluate().annotations) == set(values)
    for changes in [
        {'runeword': None},
        {'rarity': 'magic'},
        {'sockets': 3},
        {'socket_contents': 'empty'},
        {'identified': None},
        {'ethereal': True},
    ]:
        assert not evaluate(replace(item, **changes)).annotations
    for key in skills:
        wrong = {**item.stats, key: {'status': 'decoded', 'value': skills[key] - 1}}
        assert not evaluate(replace(item, stats=wrong)).annotations
    assert any('block' in c for c in r['conditions'])
    if 'Swap' in r['slot']:
        assert any('active' in c and 'swap' in c for c in r['conditions'])


def test_rhyme_source_coverage_counts_existing_grimoire_only_once():
    b = build()
    assert b['guide_demand']['summaries']['Rhyme']['distinct_builds'] >= 15
    assert b['guide_demand']['summaries']['Rhyme']['distinct_builds'] == len(
        set(b['guide_demand']['summaries']['Rhyme']['builds'])
    )

    assert (
        len([r for r in b['profiles'] if r['build'] == 'mirrored-blades-warlock-guide' and r.get('names') == ['Rhyme']])
        == 1
    )
