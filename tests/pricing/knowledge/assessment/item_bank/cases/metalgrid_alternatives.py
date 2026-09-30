"""Metalgrid defense/resistance and eligible Attack Rating; charges are not passive summons."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('berserk-barbarian', 4), ('double-throw-barbarian-guide', 6)),
    'Assassin': (('dragon-talon-assassin', 0),),
    'Sorceress': (('lightning-sorceress', 8),),
    'Paladin': (('smite-paladin', 2),),
    'Amazon': (('strafe-amazon', 3),),
}
SUFFIX = '-metalgrid-jewelry-casting-alternative'
CHARGES = ((90, 22, 11), (76, 12, 20))
RANGES = {31: (300, 350), 19: (400, 450), **dict.fromkeys((39, 41, 43, 45), (25, 35))}


def amulet(defense=300, resistance=25, attack_rating=400, *, depleted=False):
    return Item(
        'Amulet',
        'unique',
        'Metalgrid',
        (
            (31, 0, defense),
            (19, 0, attack_rating),
            *((stat, 0, resistance) for stat in (39, 41, 43, 45)),
            *((204, skill * 64 + level, (count << 8) + (0 if depleted else count)) for skill, level, count in CHARGES),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        item = amulet()
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', amulet(350, 35, 450), context, 'true'),
            ('defense-perfect', amulet(350), context, 'true'),
            ('resistance-perfect', amulet(resistance=35), context, 'true'),
            ('attack-rating-perfect', amulet(attack_rating=450), context, 'true'),
            ('depleted-charges', amulet(depleted=True), context, 'true'),
            (
                'unread-charges',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 204), complete=False),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        attack = player_class not in ('Sorceress', 'Paladin')
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                keys = ['31:0', '39:0', '41:0', '43:0', '45:0'] + (['19:0'] if attack else [])
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=RANGES[stat][0], max=RANGES[stat][1]),
                                roll_quality='perfect' if value == RANGES[stat][1] else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in RANGES
                        )
                    )
                )
            absent = {f'204:{skill * 64 + level}': configs for skill, level, _ in CHARGES}
            if not attack:
                absent['19:0'] = configs
            report = ('Metalgrid', 'Trade tier:') if truth == 'true' else ('Amulet',)
            if truth == 'true' and label != 'unread-charges':
                report += ('Iron Golem', 'Iron Maiden')
            yield Case(
                id=f'metalgrid-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-charges'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=report,
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/375',
                    'third-parties/d2data/json/skills.json:/90',
                    'third-parties/d2data/json/skills.json:/76',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Amulets/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
