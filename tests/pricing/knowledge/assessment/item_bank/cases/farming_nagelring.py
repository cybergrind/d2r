"""Nagelring farming uses keep their separate class and loadout conditions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.cases.strafe_nagelring import RING
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPIRIT = Item(
    'Monarch',
    'normal',
    'Spirit',
    ((105, 0, 25), (127, 0, 2), (99, 0, 55), (194, 0, 4)),
    sockets=4,
    socket_contents='filled',
    runeword='Spirit',
    socket_items=tuple(SocketItem(name + ' Rune') for name in ('Tal', 'Thul', 'Ort', 'Amn')),
)


def shield(item):
    return {'off_hand': normalize(item.capture()).to_dict()}


def examples():
    for role, klass, source in (
        ('enchant-mf-nagelring', 'Sorceress', '/enchant-sorceress/variants/2'),
        ('berserk-starter-nagelring', 'Barbarian', '/berserk-barbarian/variants/0'),
        ('berserk-standard-nagelring', 'Barbarian', '/berserk-barbarian/variants/1'),
        ('lightning-strike-starter-nagelring', 'Amazon', '/lightning-strike-amazon/variants/0'),
    ):
        # No Spirit or Stealskull requirement is imported from another build.
        context = {'player_class': klass, 'player_total_fcr': 0}
        for label, item, ctx, scenario, truth in (
            ('minimum-mf', RING, context, 'positive', 'true'),
            ('perfect-mf', replace(RING, raw_stats=(*RING.raw_stats[:-1], (80, 0, 30))), context, 'positive', 'true'),
            ('wrong-class', RING, {'player_class': 'Necromancer'}, 'negative', 'false'),
            ('unknown-class', RING, {}, 'unknown', 'unknown'),
            ('unread-mf', replace(RING, raw_stats=RING.raw_stats[:-1]), context, 'unknown', 'true'),
        ):
            yield role, source, label, item, ctx, scenario, truth, None
    role = 'fire-blast-standard-spirit-nagelring'
    source = '/fire-blast-assassin/variants/1'
    context = {'player_class': 'Assassin', 'player_total_fcr': 102, 'player_equipment': shield(SPIRIT)}
    for label, ctx, scenario, truth, dependency in (
        ('minimum-mf', context, 'positive', 'true', 'true'),
        (
            'superior-spirit',
            {**context, 'player_equipment': shield(replace(SPIRIT, rarity='superior'))},
            'positive',
            'true',
            'true',
        ),
        ('below-cast-breakpoint', {**context, 'player_total_fcr': 101}, 'negative', 'false', 'true'),
        ('unknown-cast-rate', {**context, 'player_total_fcr': None}, 'unknown', 'unknown', 'true'),
        ('wrong-class', {**context, 'player_class': 'Sorceress'}, 'negative', 'false', 'true'),
        ('unknown-class', {**context, 'player_class': None}, 'unknown', 'unknown', 'true'),
        ('empty-offhand', {**context, 'player_equipment': {'off_hand': None}}, 'negative', 'true', 'false'),
        ('unknown-offhand', {**context, 'player_equipment': {}}, 'unknown', 'true', 'unknown'),
        (
            'name-list-only',
            {**context, 'player_equipment': {}, 'player_items': ['Spirit']},
            'unknown',
            'true',
            'unknown',
        ),
        (
            'mercenary-spirit',
            {**context, 'player_equipment': {}, 'mercenary_equipment': shield(SPIRIT)},
            'unknown',
            'true',
            'unknown',
        ),
        (
            'wrong-base',
            {**context, 'player_equipment': shield(replace(SPIRIT, base='Crystal Sword'))},
            'negative',
            'true',
            'false',
        ),
        (
            'unknown-runeword',
            {**context, 'player_equipment': shield(replace(SPIRIT, name='Monarch', runeword=None))},
            'unknown',
            'true',
            'unknown',
        ),
        (
            'unidentified-shield',
            {**context, 'player_equipment': shield(replace(SPIRIT, identified=False))},
            'negative',
            'true',
            'false',
        ),
    ):
        yield role, source, label, RING, ctx, scenario, truth, dependency


def cases():
    for role, source, label, item, context, scenario, truth, dependency in examples():
        config = role + '-stats'
        result = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
        if dependency:
            result['dependencies'] = Contains(IsPartialDict(status=dependency))
        expected = {'roles': Contains(IsPartialDict(**result))}
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        '80:0': IsPartialDict(configuration_ids=Contains(config)),
                    }
                )
            )
        yield Case(
            id=f'farming-nagelring/{role}/{label}',
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(role,),
            scenario=scenario,
            absent_configurations=() if scenario == 'positive' else (config,),
            absent_stat_configurations={'19:0': (config,), '35:0': (config,)},
            report_contains=('Nagelring', 'Trade tier:'),
            evidence=('pricing/data/wp-a-builds.json:' + source, 'third-parties/d2data/json/uniqueitems.json:/120'),
        )


CASES = tuple(cases())
