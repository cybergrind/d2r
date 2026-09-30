"""Principle armor alternative: Ral/Gul/Eld totals and native life roll."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'blessed-hammer-paladin-player-principle-body-armors-main-alternatives-support-word-alternative'


def cases():
    context = {'player_class': 'Paladin'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Mage Plate',
            quality,
            'Principle',
            ((83, 3, 2), (7, 0, 100 * 256), (39, 0, 30), (46, 0, 5), (122, 0, 50), (198, 101 * 64 + 5, 100)),
            sockets=3,
            socket_contents='filled',
            runeword='Principle',
        )
        for label, candidate, loadout, truth in (
            ('minimum-life', item, context, 'true'),
            (
                'maximum-life',
                replace(item, raw_stats=tuple((s, p, 150 * 256 if s == 7 else v) for s, p, v in item.raw_stats)),
                context,
                'true',
            ),
            ('alternate-base', replace(item, base='Dusk Shroud'), context, 'true'),
            ('insufficient-capacity', replace(item, base='Quilted Armor'), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('empty', replace(item, socket_contents='empty'), context, 'false'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
            ('wrong-count', replace(item, sockets=2), context, 'false'),
            ('unknown-count', replace(item, sockets=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ):
            config = ROLE + '-stats'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('83:3', '7:0', '39:0', '46:0')
                        }
                    )
                )
            yield Case(
                id=f'hammer/principle/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations=dict.fromkeys(('122:0', '198:6469'), (config,)),
                report_contains=('Principle',),
                evidence=(
                    'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots/Body Armors/3',
                    'third-parties/d2data/json/runes.json:/Principle',
                    'third-parties/d2data/json/gems.json',
                ),
            )


CASES = tuple(cases())
