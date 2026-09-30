"""Skullder alternative and intrinsic Harlequin MF setup retain distinct FCR scope."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'skullder-body-armors-utility-alternative',
        Item(
            'Russet Armor',
            'unique',
            "Skullder's Ire",
            ((127, 0, 1), (240, 0, 10), (35, 0, 10), (16, 0, 160), (252, 0, 20)),
        ),
        ('127:0', '240:0', '35:0'),
    ),
    (
        '2-harlequin',
        Item('Shako', 'unique', 'Harlequin Crest', ((127, 0, 2), (80, 0, 50), (31, 0, 98))),
        ('127:0', '80:0'),
    ),
)


def cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer', specs=SPECS):
    for slug, item, keys in specs:
        role = build + '-' + slug
        config = role + '-stats'
        shako = slug == '2-harlequin'
        context = {'player_class': player_class, **({'player_total_fcr': 125} if shako else {})}
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum-defense',
                replace(
                    item,
                    raw_stats=tuple(
                        (s, p, (141 if shako else 200) if s == (31 if shako else 16) else v)
                        for s, p, v in item.raw_stats
                    ),
                ),
                context,
                'true',
            ),
            ('empty-socket', replace(item, sockets=1), context, 'true'),
            ('unknown-sockets', replace(item, sockets=None), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false' if shako else 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            (
                'wrong-class',
                item,
                {**context, 'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'},
                'false',
            ),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
        ]
        if shako:
            rows += [
                ('below-fcr', item, {**context, 'player_total_fcr': 124}, 'false'),
                ('unknown-fcr', item, {'player_class': player_class}, 'unknown'),
                ('above-fcr', item, {**context, 'player_total_fcr': 126}, 'true'),
            ]
        else:
            rows += [
                ('upgraded', replace(item, base='Balrog Skin'), context, 'true'),
                ('level99', replace(item, viewer_level=99), context, 'true'),
                (
                    'absent-repair',
                    replace(item, ethereal=True, raw_stats=item.raw_stats[:-1], complete=True),
                    context,
                    'false',
                ),
                ('unread-repair', replace(item, ethereal=True, raw_stats=item.raw_stats[:-1]), context, 'unknown'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'{prefix}/mf-armor/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations=dict.fromkeys(('16:0', '31:0'), (config,)),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = tuple(cases())
