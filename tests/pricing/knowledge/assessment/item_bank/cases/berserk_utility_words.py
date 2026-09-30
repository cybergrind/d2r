"""Harmony swap mobility and Wealth farming are distinct from attack-loadout claims."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'harmony-weapon-swap',
        Item(
            'Blade Bow',
            'normal',
            'Harmony',
            ((151, 115, 10), (17, 0, 200), (18, 0, 200), (27, 0, 20), (2, 0, 10)),
            sockets=4,
            socket_contents='filled',
            runeword='Harmony',
        ),
        ('151:115',),
        'Short Bow',
    ),
    (
        'wealth-body-armor',
        Item(
            'Dusk Shroud',
            'normal',
            'Wealth',
            ((80, 0, 100), (79, 0, 300), (2, 0, 10), (138, 0, 2)),
            sockets=3,
            socket_contents='filled',
            runeword='Wealth',
        ),
        ('80:0', '79:0', '2:0', '138:0'),
        'Quilted Armor',
    ),
)


def cases():
    context = {'player_class': 'Barbarian'}
    for slug, original, keys, too_small in SPECS:
        role = 'berserk-barbarian-player-' + slug + '-main-alternatives-word-utility-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(original, rarity=quality)
            for label, candidate, loadout, truth in (
                ('native', item, context, 'true'),
                ('insufficient-capacity', replace(item, base=too_small), context, 'false'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=item.sockets - 1), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'berserk/utility-words/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '27:0'), (role + '-stats',)),
                    report_contains=(item.name,),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/berserk-barbarian/slots',
                        'third-parties/d2data/json/runes.json',
                    ),
                )


CASES = tuple(cases())
