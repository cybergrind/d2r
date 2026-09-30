"""Barbarian class skills plus cast speed, independent of perfect socket setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'double-throw-barbarian-guide-berserker-magus'
CONFIG = ROLE + '-stats'


def cases():
    for quality in ('magic', 'rare'):
        raw = ((83, 4, 2), (105, 0, 20))
        original = Item('Diadem', quality, raw_stats=raw, affix_records=(('prefix', 579), ('suffix', 175)))
        ctx = {'player_class': 'Barbarian'}
        for label, item, context, truth in (
            ('combination', original, ctx, 'true'),
            ('circlet', replace(original, base='Circlet'), ctx, 'true'),
            (
                'one-class-skill',
                replace(original, raw_stats=((83, 4, 1), (105, 0, 20)), affix_records=None),
                ctx,
                'false',
            ),
            (
                'ten-cast-rate',
                replace(original, raw_stats=((83, 4, 2), (105, 0, 10)), affix_records=None),
                ctx,
                'false',
            ),
            (
                'warcries-only',
                replace(original, raw_stats=((188, 34, 2), (105, 0, 20)), affix_records=None, complete=True),
                ctx,
                'false',
            ),
            ('unread-skills', replace(original, raw_stats=((105, 0, 20),), affix_records=None), ctx, 'unknown'),
            ('unread-cast-rate', replace(original, raw_stats=((83, 4, 2),), affix_records=None), ctx, 'unknown'),
            (
                'known-no-cast-rate',
                replace(original, raw_stats=((83, 4, 2),), affix_records=None, complete=True),
                ctx,
                'false',
            ),
            ('two-empty-sockets', replace(original, sockets=2, raw_stats=(*raw, (194, 0, 2))), ctx, 'true'),
            ('unknown-socket-setup', replace(original, sockets=None, socket_contents='unknown'), ctx, 'true'),
            ('ethereal', replace(original, ethereal=True), ctx, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('83:4', '105:0')}
                    )
                )
            yield Case(
                id=f'berserker-magus-circlets/{quality}/{label}',
                item=item,
                context=context,
                covers=(ROLE,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(('188:34', '93:0', '17:0', '18:0'), (CONFIG,)),
                evidence=(
                    'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots/Helmets/6',
                    'third-parties/d2data/json/magicprefix.json:/579',
                    'third-parties/d2data/json/magicsuffix.json:/175',
                ),
            )


CASES = tuple(cases())
