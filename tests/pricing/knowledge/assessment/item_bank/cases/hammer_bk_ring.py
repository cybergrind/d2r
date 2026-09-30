"""Hammerdin Rings/2: BK skill/life utility does not grant spell life leech."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'blessed-hammer-paladin-bk-ring-rings-utility-alternative'
ITEM = Item(
    'Ring', 'unique', "Bul-Kathos' Wedding Band", ((127, 0, 1), (216, 0, 4 * 256), (60, 0, 3), (11, 0, 50 * 256))
)


def cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer', source_index=2):
    role = build + '-bk-ring-rings-utility-alternative'
    context = {'player_class': player_class}
    for label, item, loadout, truth in (
        ('minimum-leech', ITEM, context, 'true'),
        (
            'maximum-leech',
            replace(ITEM, raw_stats=tuple((s, p, 5 if s == 60 else v) for s, p, v in ITEM.raw_stats)),
            context,
            'true',
        ),
        ('level58', replace(ITEM, viewer_level=58), context, 'true'),
        ('level99', replace(ITEM, viewer_level=99), context, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('socketed', replace(ITEM, sockets=1), context, 'false'),
        ('unknown-sockets', replace(ITEM, sockets=None), context, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        config = role + '-stats'
        expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('127:0', '216:0')}
                )
            )
        yield Case(
            id=f'{prefix}/bk-ring/{label}',
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(role,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (config,),
            absent_stat_configurations={'60:0': (config,)},
            report_contains=(ITEM.name, 'Trade tier:') if truth == 'true' else ('Ring',),
            evidence=(
                f'pricing/data/wp-a-builds.json:/{build}/slots/Rings/{source_index}',
                'third-parties/d2data/json/uniqueitems.json:/268',
            ),
        )


CASES = tuple(cases())
