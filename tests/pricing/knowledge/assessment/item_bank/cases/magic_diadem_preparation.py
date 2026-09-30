"""Three empty sockets and the right suffix are preparation, not jewel bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SOURCES = (
    ('double-throw-barbarian-guide', 'Barbarian', 'speed', 3, 96, 30, 30, 396, 421),
    ('double-throw-barbarian-guide', 'Barbarian', 'nirvana', 4, 2, 21, 30, 245, 421),
    ('double-throw-barbarian-guide', 'Barbarian', 'luck', 5, 80, 26, 35, 289, 421),
    ('strafe-amazon', 'Amazon', 'nirvana', 1, 2, 21, 30, 245, 422),
    ('strafe-amazon', 'Amazon', 'speed', 2, 96, 30, 30, 396, 422),
)


def cases():
    for build, klass, suffix, position, stat, minimum, maximum, affix, prefix in SOURCES:
        role = f'{build}-{suffix}-diadem-socket-base'
        config = role + '-stats'
        raw = ((194, 0, 3), (stat, 0, minimum))
        item = Item('Diadem', 'magic', raw_stats=raw, sockets=3, affix_records=(('prefix', prefix), ('suffix', affix)))
        ctx = {'player_class': klass}
        for label, candidate, context, truth in (
            ('minimum', item, ctx, 'true'),
            ('perfect-suffix', replace(item, raw_stats=((194, 0, 3), (stat, 0, maximum))), ctx, 'true'),
            (
                'below-suffix',
                replace(item, raw_stats=((194, 0, 3), (stat, 0, minimum - 1)), affix_records=None),
                ctx,
                'false',
            ),
            ('unread-suffix', replace(item, raw_stats=((194, 0, 3),), affix_records=None), ctx, 'unknown'),
            (
                'known-no-suffix',
                replace(item, raw_stats=((194, 0, 3),), affix_records=None, complete=True),
                ctx,
                'false',
            ),
            (
                'two-sockets',
                replace(item, sockets=2, raw_stats=((194, 0, 2), (stat, 0, minimum)), affix_records=None),
                ctx,
                'false',
            ),
            (
                'illegal-four-sockets',
                replace(item, sockets=4, raw_stats=((194, 0, 4), (stat, 0, minimum)), affix_records=None),
                ctx,
                'false',
            ),
            (
                'unknown-sockets',
                replace(item, sockets=None, raw_stats=((stat, 0, minimum),), affix_records=None),
                ctx,
                'unknown',
            ),
            ('unknown-contents', replace(item, socket_contents='unknown'), ctx, 'unknown'),
            (
                'one-filled',
                replace(
                    item,
                    socket_contents='filled',
                    socket_items=(SocketItem('Jewel', ((93, 0, 15), (17, 0, 40), (18, 0, 40))),),
                    raw_stats=(*raw, (93, 0, 15), (17, 0, 40), (18, 0, 40)),
                ),
                ctx,
                'false',
            ),
            ('ethereal', replace(item, ethereal=True), ctx, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), ctx, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({f'{stat}:0': IsPartialDict(configuration_ids=Contains(config))})
                )
            yield Case(
                id=f'magic-diadem-preparation/{build}/{suffix}/{label}',
                item=candidate,
                context=context,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0'), (config,)),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Helmets/{position}',
                    f'third-parties/d2data/json/magicprefix.json:/{prefix}',
                    f'third-parties/d2data/json/magicsuffix.json:/{affix}',
                    'third-parties/d2data/json/armor.json:Diadem',
                ),
            )


CASES = tuple(cases())
