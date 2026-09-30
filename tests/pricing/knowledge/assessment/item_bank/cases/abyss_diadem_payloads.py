"""Captured helmet totals and actual child stats stay separate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


JEWEL_STATS = (
    (201, 387 * 64 + 25, 1),
    (357, 0, 10),
    (358, 0, 10),
    (52, 0, 15),
    (53, 0, 35),
    (85, 0, 5),
    (80, 0, 35),
    (79, 0, 50),
)
JEWEL = SocketItem('Colossal Jewel', JEWEL_STATS, complete=True, name="Guardian's Light")
RESISTS = (39, 41, 43, 45)


def cases():
    for slug, rarity in (('rare', 'rare'), ('magic', 'magic')):
        role = 'abyss-warlock-table-embedded-helmet-' + slug
        core = (
            ((83, 7, 2), (105, 0, 20), (0, 0, 30), *((s, 0, 20) for s in RESISTS), (204, 43 * 64 + 5, 32 << 8))
            if slug == 'rare'
            else ((188, 58, 3), (105, 0, 20))
        )
        core = (*core, (194, 0, 2))
        totals = (
            *core,
            *((s, layer, value) for s, layer, value in JEWEL_STATS if s != 80),
            (80, 0, 60 if slug == 'rare' else 35),
            *((s, 0, 15) for s in RESISTS if slug == 'magic'),
        )
        rune = SocketItem('Ist Rune') if slug == 'rare' else SocketItem('Um Rune')
        actual = Item(
            'Diadem', rarity, raw_stats=totals, sockets=2, socket_contents='filled', socket_items=(JEWEL, rune)
        )
        for label, item, observed in (
            ('actual', actual, True),
            ('unknown-children-observed-totals', replace(actual, socket_contents='unknown', socket_items=()), True),
            ('empty', replace(actual, raw_stats=core, socket_contents='empty', socket_items=()), False),
            ('unknown-contents', replace(actual, raw_stats=core, socket_contents='unknown', socket_items=()), False),
            ('child-only-not-parent-total', replace(actual, raw_stats=core), False),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth='true')))}
            if observed:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('357:0', '358:0', '80:0')
                        }
                    )
                )
            if label == 'actual':
                expected['facts'] = IsPartialDict(
                    socket_items=Contains(
                        IsPartialDict(
                            name="Guardian's Light",
                            stats_complete=True,
                            stats=IsPartialDict(
                                {
                                    '357:0': IsPartialDict(value=10),
                                    '358:0': IsPartialDict(value=10),
                                    '201:24793': IsPartialDict(value=1),
                                }
                            ),
                        )
                    )
                )
            yield Case(
                id=f'abyss/diadem-payloads/{slug}/{label}',
                item=item,
                context={'player_class': 'Warlock'},
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario='positive',
                absent_stat_configurations=dict.fromkeys(('52:0', '53:0', '204:2757', '201:24793'), (role + '-stats',)),
                absent_annotations=() if observed else ('357:0', '358:0'),
                report_contains=("Guardian's Light", 'Ist' if slug == 'rare' else 'Um') if label == 'actual' else (),
                evidence=('pricing/raw/mr/planners/gsg0p0l0.json',),
            )


CASES = tuple(cases())
