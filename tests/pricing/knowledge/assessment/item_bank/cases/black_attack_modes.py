"""Black Flail: Crushing Blow/IAS for both attacks; AR/cold only for kicks."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def black(quality):
    return Item(
        'Flail',
        quality,
        'Black',
        (
            (17, 0, 120),
            (18, 0, 120),
            (136, 0, 40),
            (93, 0, 15),
            (35, 0, 2),
            (19, 0, 200),
            (54, 0, 3),
            (55, 0, 14),
            (56, 0, 75),
            (3, 0, 10),
            (81, 0, 1),
            (194, 0, 3),
        ),
        runeword='Black',
        sockets=3,
        socket_contents='filled',
        socket_items=tuple(SocketItem(name) for name in ('Thul Rune', 'Io Rune', 'Nef Rune')),
    )


def cases():
    for build, klass, sources in (
        (
            'dragon-talon-assassin',
            'Assassin',
            (
                ('main-alternatives', '/dragon-talon-assassin/slots/Weapon/3'),
                ('budget', '/dragon-talon-assassin/variants/0/player/Weapon/0'),
            ),
        ),
        ('smite-paladin', 'Paladin', (('main-alternatives', '/smite-paladin/slots/Weapon/0'),)),
    ):
        roles = tuple(f'{build}-black-{variant}-source-recipe' for variant, _ in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = black(quality)
            examples = (
                ('flail', item, context, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                # Knout can hold the recipe, but is not the exact Flail source configuration.
                ('different-base', replace(item, base='Knout'), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if active:
                    priorities = [
                        ('136:0', 'desirable'),
                        ('93:0', 'desirable'),
                        ('35:0', 'supporting'),
                        ('3:0', 'supporting'),
                    ]
                    if klass == 'Assassin':
                        priorities += [(key, 'supporting') for key in ('19:0', '54:0', '55:0')]
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs), desirability=grade)
                                for key, grade in priorities
                            }
                        )
                    )
                excluded = ('17:0', '18:0') + (() if klass == 'Assassin' else ('19:0', '54:0', '55:0'))
                yield Case(
                    id=f'black-attack-modes/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    absent_stat_configurations=dict.fromkeys(excluded, configs),
                    report_contains=(
                        'Black',
                        'Flail',
                        'Thul, Io, Nef',
                        '40% Chance of Crushing Blow',
                        '15% Increased Attack Speed',
                    )
                    if active
                    else (),
                    evidence=(
                        *(f'pricing/data/wp-a-builds.json:{locator}' for _, locator in sources),
                        'third-parties/d2data/json/runes.json:/Black',
                        'third-parties/d2data/json/gems.json:/r10',
                        'third-parties/d2data/json/gems.json:/r16',
                        'third-parties/d2data/json/gems.json:/r04',
                    ),
                )


CASES = tuple(cases())
