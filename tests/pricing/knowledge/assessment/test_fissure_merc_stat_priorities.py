import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    (
        'standard-fortitude',
        'Fortitude',
        'Sacred Armor',
        4,
        ['Infinity'],
        ['17:0', '18:0', '16:0', '39:0', '41:0', '43:0', '45:0'],
    ),
    (
        'magic-find-fortitude',
        'Fortitude',
        'Sacred Armor',
        4,
        ['Infinity'],
        ['17:0', '18:0', '16:0', '39:0', '41:0', '43:0', '45:0'],
    ),
    (
        'ubers-chains-of-honor',
        'Chains of Honor',
        'Archon Plate',
        4,
        ['Infinity', 'Flickering Flame'],
        ['60:0', '39:0', '41:0', '43:0', '45:0'],
    ),
    ('ubers-flickering-flame', 'Flickering Flame', 'Bone Visage', 3, ['Infinity', 'Chains of Honor'], ['151:100']),
]


@pytest.mark.parametrize(('suffix', 'name', 'base', 'sockets', 'companions', 'keys'), CASES)
def test_fissure_merc_runeword_priorities_do_not_transfer_wearer_stats(suffix, name, base, sockets, companions, keys):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == 'fissure-merc-' + suffix)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    stats = {k: {'status': 'decoded', 'value': 10} for k in [*keys, '126:1', '333:0', '105:0', '80:0']}
    item = replace(facts(base, 'normal', name), runeword=name, sockets=sockets, socket_contents='filled', stats=stats)
    context = {'player_class': 'Druid', 'mercenary_type': 'Act 2 Might', 'mercenary_items': companions}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    for quality in ('normal', 'superior'):
        for ethereal in (True, False, None):
            result = evaluate(replace(item, rarity=quality, ethereal=ethereal))
            assert set(result.annotations) == set(keys)
            assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
            assert result.configurations[0]['role']['status'] == 'partial'
    for key in keys:
        remaining = set(keys) - ({'17:0', '18:0'} if key in ('17:0', '18:0') else {key})
        assert set(evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations) == remaining
    for changes in (
        {'name': None},
        {'name': 'Other'},
        {'runeword': None},
        {'runeword': 'Lore'},
        {'sockets': 0},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'rarity': 'magic'},
        {'identified': False},
        {'item_type': 'pelt'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in (
        {},
        {**context, 'player_class': 'Warlock'},
        {**context, 'mercenary_type': None},
        {**context, 'mercenary_type': 'Act 5 Frenzy'},
    ):
        assert not evaluate(ctx=ctx).annotations
    for companion in companions:
        assert not evaluate(
            ctx={**context, 'mercenary_items': [v for v in companions if v != companion], 'player_items': companions}
        ).annotations
    holy = evaluate(ctx={**context, 'mercenary_type': 'Act 2 Holy Freeze'})
    assert bool(holy.annotations) == ('fortitude' in suffix)
