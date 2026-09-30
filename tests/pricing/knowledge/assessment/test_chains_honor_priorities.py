from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('blessed-hammer-paladin', 3, 'player', 'Paladin', 'Archon Plate', (), None, None),
    ('echoing-strike-warlock-guide', 1, 'merc', 'Warlock', 'Archon Plate', ('Act 2 Prayer',), None, None),
    ('echoing-strike-warlock-guide', 2, 'merc', 'Warlock', 'Archon Plate', ('Act 2 Prayer',), None, None),
    ('enchant-sorceress', 1, 'merc', 'Sorceress', 'Archon Plate', ('Act 2 Prayer',), None, None),
    ('enchant-sorceress', 2, 'merc', 'Sorceress', 'Archon Plate', ('Act 2 Prayer',), None, None),
    ('fissure-druid', 3, 'player', 'Druid', 'Archon Plate', (), None, None),
    ('fissure-druid', 3, 'merc', 'Druid', 'Archon Plate', ('Act 2 Might',), None, None),
    ('fist-of-the-heavens-paladin', 3, 'merc', 'Paladin', 'Sacred Armor', ('Act 5 Frenzy',), None, None),
    ('lightning-fury-amazon-guide', 3, 'player', 'Amazon', 'Dusk Shroud', (), None, None),
    ('lightning-sorceress', 3, 'player', 'Sorceress', 'Archon Plate', (), 105, None),
    ('lightning-strike-amazon', 2, 'player', 'Amazon', 'Archon Plate', (), None, None),
    ('meteor-sorceress', 1, 'player', 'Sorceress', 'Dusk Shroud', (), 63, 60),
    ('mirrored-blades-warlock-guide', 1, 'merc', 'Warlock', 'Archon Plate', ('Act 2 Might',), None, None),
    ('nova-sorceress-guide', 1, 'merc', 'Sorceress', 'Archon Plate', ('Act 2 Might', 'Act 2 Holy Freeze'), None, None),
    ('nova-sorceress-guide', 2, 'merc', 'Sorceress', 'Archon Plate', ('Act 2 Might', 'Act 2 Holy Freeze'), None, None),
    ('nova-sorceress-guide', 3, 'player', 'Sorceress', 'Wyrmhide', (), None, None),
    ('nova-sorceress-guide', 3, 'merc', 'Sorceress', 'Archon Plate', ('Act 2 Might', 'Act 2 Holy Freeze'), None, None),
    ('smite-paladin', 1, 'player', 'Paladin', 'Archon Plate', (), None, None),
    ('smite-paladin', 2, 'player', 'Paladin', 'Archon Plate', (), None, None),
    ('strafe-amazon', 1, 'merc', 'Amazon', 'Archon Plate', ('Act 2 Might',), None, None),
    ('strafe-amazon', 2, 'merc', 'Amazon', 'Archon Plate', ('Act 2 Might',), None, None),
]


@pytest.mark.parametrize(('slug', 'index', 'side', 'cls', 'base', 'mercs', 'fcr', 'fhr'), MEMBERS)
def test_chains_honor_completed_recipe_role_and_useful_stats(slug, index, side, cls, base, mercs, fcr, fhr):
    bundle = build()
    rid = f'{slug}-{index}-{side}-chains-honor'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'127:0': 2, '36:0': 8, '39:0': 65, '41:0': 65, '43:0': 65, '45:0': 65, '60:0': 8}
    item = replace(
        facts(base, name='Chains of Honor'),
        runeword='Chains of Honor',
        sockets=4,
        socket_contents='filled',
        ethereal=side == 'merc',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls}
    if mercs:
        ctx['mercenary_type'] = mercs[0]
    if fcr:
        ctx['player_total_fcr'] = fcr
    if fhr:
        ctx['player_total_fhr'] = fhr

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == (set(values) if side == 'merc' else set(values) - {'60:0'})
    assert evaluate().annotations['39:0']['desirability'] == 'desirable'
    if side == 'merc':
        assert evaluate().annotations['60:0']['desirability'] == 'desirable'
        for merc in mercs:
            assert evaluate(context={**ctx, 'mercenary_type': merc}).annotations
        for merc in (None, 'Act 1 Fire', True):
            assert not evaluate(context={**ctx, 'mercenary_type': merc}).annotations
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    for changes in (
        {'runeword': None},
        {'runeword': 'Duress'},
        {'sockets': 3},
        {'sockets': None},
        {'socket_contents': 'empty'},
        {'socket_contents': 'unknown'},
        {'identified': None},
        {'rarity': 'magic'},
        {'ethereal': side != 'merc'},
        {'base_code': facts('Mage Plate').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for field, target in [('player_total_fcr', fcr), ('player_total_fhr', fhr)]:
        if target:
            for value in (None, target - 1, True, str(target)):
                assert not evaluate(context={**ctx, field: value}).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'


def test_chains_honor_demand_deduplicates_beneficiaries_and_keeps_conflicts_pending():
    b = build()
    d = b['guide_demand']['summaries'].get('Chains of Honor')
    assert d is not None
    assert d['distinct_builds'] >= 13
    assert d['distinct_builds'] == len(set(d['builds']))

    assert d['grade'] == 'Pending'
    assert d['lower_bound_grade'] == 'High'
    ids = {r['id'] for r in b['profiles']}
    for rid in (
        'double-throw-barbarian-guide-1-merc-chains-honor',
        'mirrored-blades-warlock-guide-2-merc-chains-honor',
        'dream-paladin-2-player-chains-honor',
    ):
        assert rid not in ids
