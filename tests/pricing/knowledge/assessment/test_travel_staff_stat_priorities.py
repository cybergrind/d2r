import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


GROUPS = {
    'Warlock': [
        'abyss-warlock-build-guide-starter-travel-staff',
        'echoing-strike-warlock-guide-starter-travel-staff',
        'mirrored-blades-warlock-guide-starter-travel-staff',
        'fire-warlock-guide-starter-charges-54',
    ],
    'Paladin': [
        'fist-of-the-heavens-paladin-foh-starter-travel-staff',
        'fist-of-the-heavens-paladin-holy-bolt-starter-travel-staff',
        'smite-paladin-standard-travel-staff',
    ],
    'Amazon': ['lightning-fury-amazon-guide-starter-charges-54', 'lightning-strike-amazon-starter-travel-staff'],
    'Druid': ['fissure-druid-starter-travel-staff'],
    'Necromancer': [
        'summoner-necromancer-guide-starter-travel-staff',
        'poison-nova-necromancer-teleport-staf',
        'poison-nova-necromancer-starter-travel-staff',
    ],
    'Assassin': [
        'dragon-talon-assassin-budget-travel-staff',
        'fire-blast-assassin-starter-travel-staff',
        'lightning-sentry-assassin-starter-travel-staff',
    ],
    'Barbarian': ['berserk-barbarian-teleport-staf'],
}
ENIGMA_ALTERNATIVES = {
    'smite-paladin-standard-travel-staff',
    'poison-nova-necromancer-teleport-staf',
    'berserk-barbarian-teleport-staf',
}


@pytest.mark.parametrize(('klass', 'role'), [(k, r) for k, roles in GROUPS.items() for r in roles])
def test_travel_staff_markers_preserve_class_charges_and_enigma_alternatives(klass, role):
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == role)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    context = {'player_class': klass, 'player_items': []}

    def evaluate(stats, context=context, **changes):
        item = replace(facts('Long Staff', 'magic'), stats=stats, **changes)
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [profile], context)
        )

    for quality in ('magic', 'rare'):
        result = evaluate({'204:3457': charged(1)}, rarity=quality)
        assert set(result.annotations) == {'204:3457'}
        assert result.annotations['204:3457']['roll_quality'] == 'unassessed'
        assert result.configurations[0]['role']['status'] == 'partial'
        assert any('Ethereal' in v for v in result.configurations[0]['role']['missing'])
    for ethereal in (True, None):
        assert evaluate({'204:3457': charged(1)}, ethereal=ethereal).annotations
    for stats in ({'204:3457': charged(0)}, {}, {'204:5253': charged(1)}, {'204:3457': {**charged(1), 'value': 2}}):
        assert not evaluate(stats).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate({'204:3457': charged(1)}, context).annotations
    for changes in (
        {'rarity': 'unique'},
        {'identified': False},
        {'item_type': 'wand'},
        {'gaps': ['Duplicate native stat 204:3457.']},
    ):
        assert not evaluate({'204:3457': charged(1)}, **changes).annotations
    if role in ENIGMA_ALTERNATIVES:
        for context in ({'player_class': klass}, {'player_class': klass, 'player_items': ['Enigma']}):
            assert not evaluate({'204:3457': charged(1)}, context).annotations
        assert evaluate({'204:3457': charged(1)}, {'player_class': klass, 'player_items': ['Bramble']}).annotations
