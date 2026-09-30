"""Fissure table armor preserves caster recipients, native procs and linked gems."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    (
        'smoke',
        'Smoke',
        'Archon Plate',
        ('Nef', 'Lum'),
        ((39, 0, 50), (41, 0, 50), (43, 0, 50), (45, 0, 50), (99, 0, 20), (16, 0, 75), (32, 0, 250), (1, 0, 10)),
        ('39:0', '41:0', '43:0', '45:0', '99:0', '16:0', '32:0', '1:0'),
    ),
    (
        'treachery',
        'Treachery',
        'Archon Plate',
        ('Shael', 'Thul', 'Lem'),
        ((201, 17103, 5), (99, 0, 20), (43, 0, 30), (93, 0, 45), (83, 6, 2)),
        ('201:17103', '99:0', '43:0'),
    ),
    (
        'vipermagi',
        'Skin of the Vipermagi',
        'Serpentskin Armor',
        (),
        ((127, 0, 1), (105, 0, 30), (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20), (35, 0, 9), (16, 0, 120)),
        ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0', '35:0', '16:0'),
    ),
    ('perfect-topaz', None, 'Dusk Shroud', ('Perfect Topaz',) * 4, ((80, 0, 96),), ('80:0',)),
)


def cases():
    for slug, name, base, fillers, stats, keys in SPECS:
        role = f'fissure-druid-{slug}-general-armor'
        unique = slug == 'vipermagi'
        topaz = slug == 'perfect-topaz'
        for quality in ('unique',) if unique else ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                name,
                stats,
                sockets=len(fillers),
                socket_contents='filled' if fillers else 'empty',
                runeword=name if fillers and not topaz else None,
                socket_items=tuple(SocketItem(n if topaz else n + ' Rune') for n in fillers),
            )
            variants = [
                ('native', item, 'Druid', True),
                ('ethereal', replace(item, ethereal=True), 'Druid', False),
                ('unknown-class', item, None, False),
                ('wrong-class', item, 'Paladin', False),
            ]
            if fillers:
                variants += [
                    ('empty', replace(item, runeword=None, socket_contents='empty', socket_items=()), 'Druid', False)
                ]
            if topaz:
                variants += [
                    ('wrong-gems', replace(item, socket_items=(SocketItem('Perfect Ruby'),) * 4), 'Druid', False),
                    ('wrong-base', replace(item, base='Monarch'), 'Druid', False),
                    ('unverified-payload', replace(item, socket_items=item.socket_items[:3]), 'Druid', False),
                ]
            elif unique:
                variants += [('upgraded', replace(item, base='Wyrmhide'), 'Druid', True)]
            else:
                variants += [('alternative-base', replace(item, base='Dusk Shroud'), 'Druid', True)]
            for label, candidate, cls, usable in variants:
                yield Case(
                    id=f'fissure-armor-tail/{slug}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': cls},
                    covers=(role,),
                    scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                                )
                            )
                        )
                    }
                    if usable
                    else {'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, status='failed')))}
                    if label == 'wrong-gems'
                    else {},
                    absent_annotations=('93:0',) if slug == 'treachery' and usable else (),
                    absent_configurations=() if usable else (role + '-stats',),
                    absent_stat_configurations={'93:0': (role + '-stats',), '83:6': (role + '-stats',)}
                    if slug == 'treachery'
                    else {},
                    evidence=('pricing/raw/mr/guides__fissure-druid.html:Gear Options / Body Armor',),
                )


CASTER_CASES = tuple(cases())
MERCENARY_CASES = tuple(
    replace(
        case,
        id=case.id.removesuffix('/native') + '/known-mercenary',
        context={'player_class': 'Druid', 'mercenary_type': 'Act 2 Prayer'},
        expected={
            'assessment': IsPartialDict(
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {'93:0': IsPartialDict(configuration_ids=Contains('fissure-starter-merc-treachery-stats'))}
                    )
                )
            )
        },
        absent_annotations=(),
        covers=('fissure-starter-merc-treachery',),
    )
    for case in CASTER_CASES
    if '/treachery/' in case.id and case.id.endswith('/native')
)


def mercenary_boundaries():
    role = 'fissure-starter-merc-treachery'
    for original in MERCENARY_CASES:
        item, ctx = original.item, original.context
        for label, candidate, context, truth in (
            ('ethereal', replace(item, ethereal=True), ctx, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), ctx, 'true'),
            ('wrong-class', item, {**ctx, 'player_class': 'Paladin'}, 'false'),
            ('unknown-class', item, {**ctx, 'player_class': None}, 'unknown'),
            ('unidentified', replace(item, identified=False), ctx, 'false'),
            ('empty', replace(item, runeword=None, socket_contents='empty', socket_items=()), ctx, 'false'),
            ('conflicting-sockets', replace(item, sockets=2), ctx, 'unknown'),
        ):
            yield replace(
                original,
                id=original.id.removesuffix('/known-mercenary') + '/merc-' + label,
                item=candidate,
                context=context,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
                    )
                },
                absent_configurations=() if truth == 'true' else (role + '-stats',),
            )
        for label, merc in (('unknown-bearer', None), ('caster', 'Act 3 Fire')):
            yield replace(
                original,
                id=original.id.removesuffix('/known-mercenary') + '/merc-' + label,
                context={**ctx, 'mercenary_type': merc},
                scenario='unknown' if merc is None else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    '201:17103': IsPartialDict(configuration_ids=Contains(role + '-stats')),
                                    '43:0': IsPartialDict(configuration_ids=Contains(role + '-stats')),
                                }
                            )
                        )
                    )
                },
                absent_stat_configurations={'93:0': (role + '-stats',), '83:6': (role + '-stats',)},
            )


CASES = (*CASTER_CASES, *MERCENARY_CASES, *mercenary_boundaries())
