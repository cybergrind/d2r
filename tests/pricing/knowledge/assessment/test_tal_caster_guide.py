from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


PIECES = (
    "Tal Rasha's Guardianship",
    "Tal Rasha's Horadric Crest",
    "Tal Rasha's Fine-Spun Cloth",
    "Tal Rasha's Lidless Eye",
    "Tal Rasha's Adjudication",
)


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'intrinsic', 'partial'),
    [
        (
            PIECES[0],
            'Lacquered Plate',
            6,
            {'80:0': 88, '39:0': 40, '41:0': 40, '43:0': 40, '35:0': 15, '31:0': 400},
            {'105:0': 10},
        ),
        (
            PIECES[1],
            'Death Mask',
            4,
            {'7:0': 60, '9:0': 30, '31:0': 45, '39:0': 15, '41:0': 15, '43:0': 15, '45:0': 15},
            {},
        ),
        (PIECES[2], 'Mesh Belt', 4, {'9:0': 30, '2:0': 20, '114:0': 37, '80:0': 10}, {'31:0': 60, '105:0': 10}),
        (
            PIECES[3],
            'Swirling Crystal',
            4,
            {'7:0': 57, '9:0': 77, '1:0': 10, '105:0': 20},
            {'83:1': 1, '333:0': 15, '331:0': 15},
        ),
    ],
)
def test_tal_native_caster_stats_and_distinct_piece_activation(name, base, count, intrinsic, partial):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-tal-caster-gear')]
    assert len(roles) == count
    for role in roles:
        fire = role['build'] in ('fire-wall-sorceress-guide', 'hydra-sorceress', 'frozen-orb-meteor-sorceress')
        cold = role['build'] in ('frozen-orb-sorceress', 'frozen-orb-meteor-sorceress')
        expected = dict(intrinsic)
        if name == PIECES[3]:
            if fire:
                expected['107:61'] = 1
            if cold:
                expected['107:65'] = 1
        values = {**intrinsic, **partial, '107:61': 1, '107:63': 2, '107:65': 1, '60:0': 10, '62:0': 10, '334:0': 15}
        item = replace(
            facts(base, 'set', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate=item, items=(), configs=configs, role=role, klass=klass):
            ctx = {'player_class': klass, 'player_items': list(items)}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        if name == PIECES[3]:
            assert not evaluate().annotations
        else:
            assert set(evaluate().annotations) == set(expected)
        companions = [p for p in PIECES if p != name and (klass == 'Sorceress' or p != PIECES[3])]
        full = set(expected)
        if name == PIECES[0]:
            full.add('105:0')
        if name == PIECES[2]:
            full.update(('31:0', '105:0'))
        if name == PIECES[3]:
            full.add('83:1')
            if fire:
                full.add('333:0')
            if cold:
                full.add('331:0')
        assert set(evaluate(items=companions).annotations) == full
        for key, value in partial.items():
            weak = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value - 1}})
            assert key not in evaluate(weak, companions).annotations
        repeated = evaluate(items=[companions[0]] * 4)
        if name == PIECES[2]:
            assert '31:0' in repeated.annotations
            assert '105:0' not in repeated.annotations
        if name == PIECES[3]:
            assert '83:1' in repeated.annotations
            assert not {'333:0', '331:0'} & repeated.annotations.keys()
        if klass == 'Warlock':
            assert '105:0' not in evaluate(items=[PIECES[3]]).annotations
        if name == PIECES[3] and fire:
            assert '333:0' in evaluate(items=companions[:2]).annotations
            assert '331:0' not in evaluate(items=companions[:2]).annotations
        assert not evaluate(replace(item, ethereal=True), companions).annotations
        assert not evaluate(replace(item, rarity='unique'), companions).annotations
