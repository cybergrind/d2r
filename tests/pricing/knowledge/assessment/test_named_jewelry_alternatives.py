from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count'),
    [
        ("Highlord's Wrath", 8),
        ("The Cat's Eye", 5),
        ('Metalgrid', 6),
        ("Seraph's Hymn", 4),
        ('Telling of Beads', 4),
        ("Nature's Peace", 6),
        ('The Oculus', 4),
    ],
)
def test_named_alternatives_keep_build_stat_exceptions_and_native_identity(name, count):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-jewelry-casting-alternative')
    ]
    assert len(roles) == count
    orb = name == 'The Oculus'
    base = 'Swirling Crystal' if orb else ('Ring' if name == "Nature's Peace" else 'Amulet')
    quality = 'set' if name == 'Telling of Beads' else 'unique'
    all_keys = {key for role in roles for key in role['important_stats']}
    values = dict.fromkeys(all_keys | {'250:0', '19:0', '121:0', '123:0'}, 1)
    values['250:0'] = 0.375
    item = replace(facts(base, quality, name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, configs=configs, context=context):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        annotations = evaluate(item).annotations
        assert set(annotations) == set(role['important_stats'])
        assert bool(evaluate(replace(item, ethereal=True)).annotations) is orb
        assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
        assert not evaluate(replace(item, sockets=2)).annotations
        if name == "Highlord's Wrath":
            assert ('250:0' in annotations) is (role['build'] != 'dragon-talon-assassin')
        if name == 'Metalgrid':
            assert ('19:0' in annotations) is (role['build'] not in ('smite-paladin', 'lightning-sorceress'))
        if name == "Seraph's Hymn":
            assert ('121:0' in annotations) is (role['build'] == 'dream-paladin')
