"""Chains of Honor: distinct MF mercenary sources and nonethereal Uber player armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.fissure_coh import STATS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    for side, variant in (('merc', 2), ('player', 3)):
        role = f'blessed-hammer-paladin-{variant}-{side}-chains-honor'
        config = role + '-stats'
        context = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Holy Freeze'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Archon Plate',
                quality,
                'Chains of Honor',
                STATS,
                ethereal=side == 'merc',
                sockets=4,
                socket_contents='filled',
                runeword='Chains of Honor',
            )
            examples = [
                ('native', item, context, 'true'),
                ('opposite-ethereal', replace(item, ethereal=side != 'merc'), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('different-base', replace(item, base='Dusk Shroud'), context, 'false'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=3), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Holy Freeze'}, 'unknown'),
            ]
            if side == 'merc':
                examples.extend(
                    [
                        ('prose-sacred-ethereal', replace(item, base='Sacred Armor'), context, 'true'),
                        (
                            'prose-sacred-nonethereal',
                            replace(item, base='Sacred Armor', ethereal=False),
                            context,
                            'true',
                        ),
                        (
                            'prose-sacred-unknown-ethereal',
                            replace(item, base='Sacred Armor', ethereal=None),
                            context,
                            'unknown',
                        ),
                        ('wrong-merc', item, {**context, 'mercenary_type': 'Act 2 Might'}, 'false'),
                        ('unknown-merc', item, {'player_class': 'Paladin'}, 'unknown'),
                    ]
                )
            else:
                examples.extend(
                    [
                        ('merc-prose-base-not-player-base', replace(item, base='Sacred Armor'), context, 'false'),
                        ('no-merc-required', item, {'player_class': 'Paladin'}, 'true'),
                    ]
                )
            for label, candidate, loadout, truth in examples:
                keys = ('127:0', '36:0', '39:0', '41:0', '43:0', '45:0')
                if side == 'merc':
                    keys += ('60:0', '80:0')
                expected = {'roles': Contains(IsPartialDict(id=role, side=side, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'hammer/coh/{side}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations={'60:0': (config,)} if side == 'player' else {},
                    report_contains=('Chains of Honor',),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/variants/{variant}',
                        'third-parties/d2data/json/runes.json:/Chains of Honor',
                        'third-parties/d2data/json/gems.json',
                    ),
                )


CASES = tuple(cases())
