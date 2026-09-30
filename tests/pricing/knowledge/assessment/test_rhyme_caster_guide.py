from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('slot', 'count'), [('Off-Hand', 7), ('Off-Hand-Swap', 4)])
def test_rhyme_caster_preserves_shield_class_and_source_base(slot, count):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['slot'] == slot and r['id'].endswith('-rhyme-caster-gear')]
    assert len(roles) == count
    values = {
        '153:0': 1,
        '102:0': 40,
        '20:0': 20,
        '39:0': 25,
        '41:0': 25,
        '43:0': 25,
        '45:0': 25,
        '80:0': 25,
        '79:0': 50,
        '27:0': 15,
    }
    item = replace(
        facts('Bone Shield', 'normal', 'Rhyme'),
        runeword='Rhyme',
        sockets=2,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '105:0': 20, '60:0': 5}.items()},
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, role=role, configs=configs):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        for patch in (
            {'rarity': 'magic'},
            {'ethereal': True},
            {'socket_contents': 'empty'},
            {'sockets': 3},
            {'runeword': None},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        for base in ('Grimoire', 'Preserved Head', 'Sacred Targe'):
            alternative = facts(base)
            result = evaluate(replace(item, base_code=alternative.base_code, item_type=alternative.item_type))
            allowed = (base == 'Grimoire' and klass == 'Warlock') or (
                base == 'Preserved Head' and klass == 'Necromancer'
            )
            assert bool(result.annotations) == (allowed and not role.get('base_codes'))
        assert not evaluate(item, 'Barbarian').annotations
