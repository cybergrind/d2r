"""Sling and Gheed's Wager casting alternatives, from native415/418 and guide slots."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'sling',
        Item(
            'Ring', 'unique', 'Sling', ((97, 411, 1), (105, 0, 10), (358, 0, 3), (1, 0, 10), (150, 0, 15), (80, 0, 10))
        ),
        ('105:0', '358:0', '1:0', '80:0'),
        ('150:0',),
        {358: 5, 1: 15, 80: 20},
    ),
    (
        'gheed-s-wager',
        Item(
            'Troll Belt',
            'unique',
            "Gheed's Wager",
            (
                (105, 0, 10),
                (99, 0, 10),
                (96, 0, 10),
                (16, 0, 90),
                (358, 0, 3),
                (79, 0, 44),
                *((s, 0, 5) for s in (39, 41, 43, 45)),
            ),
        ),
        ('105:0', '99:0', '96:0', '358:0', '39:0'),
        (),
        {105: 20, 99: 20, 96: 20, 16: 150, 358: 7, 79: 75, 39: 15, 41: 15, 43: 15, 45: 15},
    ),
)


def cases(*, player_class='Paladin', build='blessed-hammer-paladin', prefix='hammer', specs=SPECS):
    context = {'player_class': player_class}
    for slug, item, keys, excluded, maxima in specs:
        role = build + '-' + slug + '-caster-utility-alternative'
        config = role + '-stats'
        for label, candidate, loadout, truth in (
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, p, maxima.get(s, v)) for s, p, v in item.raw_stats)),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('invalid-sockets', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'{prefix}/rotw-accessories/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else (item.base,),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


# Same native item boundaries; the damage type changes the independently reviewed priority set.
FIRE_WAGER = (
    SPECS[1][0],
    SPECS[1][1],
    ('105:0', '99:0', '96:0', '16:0', '39:0', '41:0', '43:0', '45:0', '79:0'),
    ('358:0',),
    SPECS[1][4],
)
CASES = (
    *cases(),
    *cases(player_class='Warlock', build='fire-warlock-guide', prefix='fire-warlock', specs=(FIRE_WAGER,)),
)
