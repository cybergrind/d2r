import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.maintenance.stat_dispositions import validate_stat_dispositions
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.assessment.test_starter_set_roles import SET_CASES


CASES = [row for row in SET_CASES if row[1] in ("Sigon's Visor", "Sigon's Sabot")]


@pytest.mark.parametrize(('slug', 'name', 'base', 'klass', 'members'), CASES)
def test_sigon_attack_rating_marker_preserves_companions_and_helmet_payload(slug, name, base, klass, members):
    document = build()
    profiles = document['profiles']
    role_id = f'{slug}-starter-set-{name}'
    role = next(p for p in profiles if p['id'] == role_id)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    key = '224:0' if name == "Sigon's Visor" else '19:0'
    item = replace(facts(base, 'set', name), stats={key: {'status': 'decoded', 'value': 8 if key == '224:0' else 50}})
    context = {'player_class': klass, 'player_items': [n for n, _ in members]}
    if name == "Sigon's Visor":
        child = (
            {'name': 'Ort Rune', 'item_type': 'rune'}
            if slug == 'strafe-amazon'
            else {
                'name': 'Jewel of Fervor',
                'item_type': 'jewl',
                'stats_complete': True,
                'stats': {'93:0': {'status': 'decoded', 'value': 15}},
            }
        )
        item = replace(item, sockets=1, socket_contents='filled', socket_items=[child])

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == {key}
    assert result.annotations[key]['desirability'] == 'desirable'
    assert result.annotations[key]['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'ring'},
        {'identified': False},
        {'stats': {}},
        {'stats': {key: {'status': 'decoded', 'value': 0}}},
        {'gaps': [f'Duplicate native stat {key}.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={'player_class': klass}).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Sorceress'}).annotations
    for companion in set(context['player_items']) - {name}:
        assert not evaluate(
            ctx={
                **context,
                'player_items': [v for v in context['player_items'] if v != companion],
                'mercenary_items': context['player_items'],
            }
        ).annotations
    if name == "Sigon's Visor":
        for changes in (
            {'socket_items': []},
            {'socket_contents': 'empty'},
            {'socket_items': [{'name': 'El Rune', 'item_type': 'rune'}]},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        if slug != 'strafe-amazon':
            # Parent IAS cannot establish the cited child jewel.
            assert not evaluate(
                replace(item, socket_items=[], stats={**item.stats, '93:0': {'status': 'decoded', 'value': 15}})
            ).annotations


def test_sigon_wrap_enables_combination_without_inventing_stat_priority():
    document = build()
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_dispositions.json').read_text())
    result = validate_stat_dispositions(reviews, document, root=ROOT)
    assert result["berserk-barbarian-starter-set-Sigon's Wrap"]['state'] == 'excluded'
