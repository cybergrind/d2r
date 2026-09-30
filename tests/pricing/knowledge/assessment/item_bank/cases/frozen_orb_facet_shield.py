"""Separate the empty deflecting base from four actual cold Rainbow Facets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


PREFIX = 'frozen-orb-sorceress-specialist-shield-cold-'
RAW = ((20, 0, 20), (102, 0, 30), (194, 0, 4))
EMPTY = Item('Monarch', 'magic', raw_stats=RAW, sockets=4, affix_records=(('prefix', 422), ('suffix', 173)))


def facet(roll=3):
    return SocketItem(
        'Jewel',
        ((54, 0, 24), (55, 0, 38), (56, 0, 75), (335, 0, roll), (331, 0, roll), (197, (59 << 6) | 37, 100)),
        complete=True,
        name='Rainbow Facet',
        unique_table_id=393,
    )


def filled(roll=3):
    return replace(
        EMPTY,
        raw_stats=(*RAW, (331, 0, roll * 4), (335, 0, roll * 4)),
        socket_contents='filled',
        socket_items=(facet(roll),) * 4,
    )


def cases():
    context = {'player_class': 'Sorceress'}
    for suffix, item in (('empty', EMPTY), ('filled', filled())):
        role = PREFIX + suffix
        config = role + '-stats'
        variants = [
            ('matching', item, context, 'true', 'true'),
            (
                'weaker-blocking-suffix',
                replace(
                    item,
                    raw_stats=tuple(
                        (stat, layer, 10 if stat == 20 else 15 if stat == 102 else value)
                        for stat, layer, value in item.raw_stats
                    ),
                    affix_records=None,
                ),
                context,
                'false',
                None,
            ),
            (
                'three-sockets',
                replace(
                    item,
                    sockets=3,
                    raw_stats=tuple(
                        (stat, layer, 3 if stat == 194 else 9 if stat in (331, 335) else value)
                        for stat, layer, value in item.raw_stats
                    ),
                    socket_items=item.socket_items[:3],
                    affix_records=None,
                ),
                context,
                'false',
                None,
            ),
            (
                'missing-block',
                replace(
                    item,
                    raw_stats=tuple(row for row in item.raw_stats if row[0] != 20),
                    affix_records=None,
                    complete=True,
                ),
                context,
                'false',
                None,
            ),
            (
                'unread-block',
                replace(item, raw_stats=tuple(row for row in item.raw_stats if row[0] != 20), affix_records=None),
                context,
                'unknown',
                None,
            ),
            ('ethereal', replace(item, ethereal=True), context, 'false', None),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', None),
            (
                'unknown-sockets',
                replace(
                    item,
                    sockets=None,
                    socket_contents='unknown',
                    raw_stats=tuple(row for row in item.raw_stats if row[0] != 194),
                ),
                context,
                'unknown',
                None,
            ),
            ('wrong-class', item, {'player_class': 'Amazon'}, 'false', None),
            ('unknown-class', item, {}, 'unknown', None),
            ('unidentified', replace(item, identified=False), context, 'false', None),
        ]
        if suffix == 'filled':
            fire = SocketItem(
                'Jewel', ((329, 0, 3), (333, 0, 3)), complete=True, name='Rainbow Facet', unique_table_id=394
            )
            variants.extend(
                (
                    ('perfect-four', filled(5), context, 'true', 'true'),
                    (
                        'one-wrong-element',
                        replace(item, socket_items=(*item.socket_items[:3], fire)),
                        context,
                        'true',
                        'false',
                    ),
                    ('unread-fourth', replace(item, socket_items=item.socket_items[:3]), context, 'true', 'unknown'),
                    ('totals-only', replace(item, socket_items=()), context, 'true', 'unknown'),
                    ('empty-not-completed', EMPTY, context, 'false', None),
                )
            )
        else:
            variants.append(('filled-not-empty', filled(), context, 'false', None))
        for label, candidate, ctx, truth, dependency in variants:
            active = truth == dependency == 'true'
            role_expected = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
            if suffix == 'filled' and dependency is not None:
                role_expected['dependencies'] = Contains(IsPartialDict(status=dependency))
            expected = {'roles': Contains(IsPartialDict(**role_expected))}
            if active:
                keys = ('20:0', '102:0', '331:0', '335:0') if suffix == 'filled' else ('20:0', '102:0')
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            scenario = (
                'positive' if active else 'unknown' if truth == 'unknown' or dependency == 'unknown' else 'negative'
            )
            yield Case(
                id=f'frozen-orb-facet-shield/{suffix}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                report_contains=('Monarch', 'Sockets: 4', *(('Rainbow Facet',) if suffix == 'filled' else ()))
                if active
                else (),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__frozen-orb-sorceress.html/sections/29',
                    'pricing/raw/mr/planners/t90106li.json:/data',
                    'third-parties/d2data/json/uniqueitems.json:/393',
                ),
            )


CASES = tuple(cases())
