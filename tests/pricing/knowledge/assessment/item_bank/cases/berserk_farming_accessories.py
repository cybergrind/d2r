"""Berserk main-table alternatives: farming utility and defensive absorb."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'chance-guards-find-absorb-alternative',
        Item('Chain Gloves', 'unique', 'Chance Guards', ((80, 0, 25), (79, 0, 200), (19, 0, 25))),
        ('80:0',),
        ('Heavy Bracers', 'Vambraces'),
        80,
        40,
    ),
    (
        'goldwrap-find-absorb-alternative',
        Item('Heavy Belt', 'unique', 'Goldwrap', ((80, 0, 30), (79, 0, 50), (93, 0, 10))),
        ('80:0', '93:0'),
        ('Battle Belt', 'Troll Belt'),
        79,
        80,
    ),
    (
        'dwarf-star-defensive-alternative',
        Item('Ring', 'unique', 'Dwarf Star', ((142, 0, 15), (35, 0, 12), (7, 0, 40 * 256), (79, 0, 100))),
        ('142:0', '35:0', '7:0'),
        (),
        35,
        15,
    ),
)


def cases(build='berserk-barbarian', player_class='Barbarian', prefix='berserk', specs=SPECS, excluded=('79:0',)):
    context = {'player_class': player_class}
    for slug, item, keys, upgrades, variable, maximum in specs:
        role = build + '-' + slug
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(
                    item, raw_stats=tuple((s, layer, maximum if s == variable else v) for s, layer, v in item.raw_stats)
                ),
                context,
                'true',
            ),
            ('invalid-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        rows += [(base, replace(item, base=base), context, 'true') for base in upgrades]
        for label, candidate, loadout, truth in rows:
            invalid_dwarf = candidate.name == 'Dwarf Star' and label in ('invalid-socket', 'ethereal')
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if invalid_dwarf:
                expected['trade_qualification'] = IsPartialDict(status='unresolved')
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'{prefix}/farming-accessories/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(excluded, (role + '-stats',)),
                report_contains=('Trade tier:',) if candidate.identified and not invalid_dwarf else (),
                report_absent=('Trade tier:', 'Trade: ordinary candidate', 'Trade: premium candidate')
                if invalid_dwarf
                else (),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
