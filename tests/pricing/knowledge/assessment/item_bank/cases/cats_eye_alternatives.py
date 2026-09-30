"""The Cat's Eye fixed attack-speed, movement and dexterity utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('double-throw-barbarian-guide', 1),),
    'Assassin': (('dragon-talon-assassin', 2),),
    'Amazon': (('lightning-fury-amazon-guide', 1), ('lightning-strike-amazon', 1), ('strafe-amazon', 2)),
}
SUFFIX = '-the-cat-s-eye-jewelry-casting-alternative'


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = Item(
            'Amulet',
            'unique',
            "The Cat's Eye",
            ((93, 0, 20), (96, 0, 30), (2, 0, 25), (31, 0, 100), (32, 0, 100)),
            complete=True,
        )
        context = {'player_class': player_class}
        examples = (
            ('fixed-bonuses', item, context, 'true'),
            (
                'unread-dexterity',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 2), complete=False),
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
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                stats = {f'{stat}:0': value for stat, _, value in candidate.raw_stats}
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in stats}
                    )
                )
                expected['facts'] = IsPartialDict(
                    stats=IsPartialDict({key: IsPartialDict(value=value) for key, value in stats.items()})
                )
            absent = {'105:0': configs}
            if label == 'unread-dexterity':
                absent['2:0'] = configs
            yield Case(
                id=f'cats-eye-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-dexterity'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else ('Amulet',),
                report_absent=('Faster Cast Rate',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/269',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Amulets/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
