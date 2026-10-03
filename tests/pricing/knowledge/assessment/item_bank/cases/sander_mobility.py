"""Exceptional early movement boots retain standalone use and visible tiers."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BOOTS = Item(
    'Heavy Boots',
    'set',
    "Sander's Riprap",
    ((96, 0, 40), (19, 0, 100), (0, 0, 5), (2, 0, 10)),
    named_table_id=124,
)
CAVEAT = (
    'Attack Rating helps direct weapon hits, not spells or the guaranteed explosion component of an exploding '
    'projectile. Strength and Dexterity support equip requirements; no set completion is inferred.'
)


def cases():
    for build, klass, index in (
        ('double-throw-barbarian-guide', 'Barbarian', 5),
        ('enchant-sorceress', 'Sorceress', 4),
    ):
        role = f'{build}-sander-s-riprap-boots-belts-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        examples = (
            ('normal-base', BOOTS, context, 'true'),
            ('exceptional-base', replace(BOOTS, base='Sharkskin Boots'), context, 'true'),
            ('elite-base', replace(BOOTS, base='Scarabshell Boots'), context, 'true'),
            ('impossible-ethereal', replace(BOOTS, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(BOOTS, ethereal=None), context, 'unknown'),
            ('socketed', replace(BOOTS, sockets=1), context, 'false'),
            ('unknown-sockets', replace(BOOTS, sockets=None), context, 'unknown'),
            ('wrong-class', BOOTS, {'player_class': 'Paladin'}, 'false'),
            ('unknown-class', BOOTS, {}, 'unknown'),
            ('unidentified', replace(BOOTS, identified=False), context, 'false'),
        )
        for label, item, loadout, truth in examples:
            active = truth == 'true'
            expected = {}
            if label != 'unidentified':
                expected['roles'] = Contains(
                    IsPartialDict(
                        id=role,
                        slot='Boots',
                        rule_trace=IsPartialDict(truth=truth),
                        missing=Contains(CAVEAT),
                    )
                )
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(
                                        configuration_id=config,
                                        desirability='desirable' if key == '96:0' else 'supporting',
                                    )
                                )
                            )
                            for key in ('96:0', '19:0', '0:0', '2:0')
                        }
                    )
                )
            yield Case(
                id=f'sander-mobility/{build}/{label}',
                item=item,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations={'127:0': (config,), '93:0': (config,)},
                report_contains=(
                    'Trade tier: low',
                    'Leveling: high',
                    'no companion set piece is needed.',
                    '+40% Faster Run/Walk',
                    '+100 to Attack Rating',
                    '+5 to Strength',
                    '+10 to Dexterity',
                )
                if active
                else (),
                report_absent=(
                    'Leveling: high — player, barbarian,',
                    'Leveling: high — player, sorceress,',
                ),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Boots/{index}',
                    "third-parties/d2data/json/setitems.json:/McAuley's Riprap",
                ),
            )


CASES = tuple(cases())
