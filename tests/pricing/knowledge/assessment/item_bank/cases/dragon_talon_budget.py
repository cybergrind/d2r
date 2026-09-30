"""Budget kicker armor and upgraded boots, including unavailable setup facts."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for slug, item in (
        (
            'duress',
            Item(
                'Dusk Shroud',
                'normal',
                'Duress',
                ((136, 0, 15), (39, 0, 15), (41, 0, 15), (43, 0, 45), (45, 0, 15), (194, 0, 3)),
                sockets=3,
                socket_contents='filled',
                runeword='Duress',
                socket_items=tuple(SocketItem(n + ' Rune') for n in ('Shael', 'Um', 'Thul')),
            ),
        ),
        ('goblin-toe', Item('Mirrored Boots', 'unique', 'Goblin Toe', ((136, 0, 25), (16, 0, 50)))),
    ):
        role = 'dragon-talon-budget-' + slug
        for quality in ('normal', 'superior', 'low_quality') if slug == 'duress' else ('unique',):
            native = replace(item, rarity=quality)
            examples = [
                ('native', native, 'Assassin', 'true', True),
                ('ethereal', replace(native, ethereal=True), 'Assassin', 'false', False),
                ('unknown-ethereal', replace(native, ethereal=None), 'Assassin', 'unknown', False),
                ('wrong-class', native, 'Paladin', 'false', False),
                ('unknown-class', native, None, 'unknown', False),
                ('unidentified', replace(native, identified=False), 'Assassin', 'false', False),
            ]
            if slug == 'duress':
                examples += [
                    (
                        'empty',
                        replace(native, runeword=None, socket_contents='empty', socket_items=()),
                        'Assassin',
                        'false',
                        False,
                    ),
                    ('alternative-base', replace(native, base='Archon Plate'), 'Assassin', 'false', False),
                ]
            else:
                examples += [('needs-upgrade', replace(native, base='Light Plated Boots'), 'Assassin', 'true', False)]
            for label, candidate, klass, truth, useful in examples:
                expectation = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if useful:
                    expectation['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in (
                                    ('136:0', '39:0', '41:0', '43:0', '45:0') if slug == 'duress' else ('136:0',)
                                )
                            }
                        )
                    )
                yield Case(
                    id=f'dragon-talon-budget/{slug}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': klass},
                    covers=(role,),
                    scenario='positive' if useful else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expectation)},
                    absent_configurations=() if useful else (role + '-stats',),
                    report_contains=(
                        ('Goblin Toe', 'Trade tier:', 'Upgrade to Mirrored Boots')
                        if label == 'needs-upgrade'
                        else ('Goblin Toe', 'Trade tier:')
                        if slug == 'goblin-toe' and candidate.identified
                        else (candidate.name,)
                    ),
                    report_absent=('Trade tier:',) if slug == 'goblin-toe' and not candidate.identified else (),
                    evidence=('pricing/data/wp-a-builds.json:/dragon-talon-assassin/variants/0',),
                )


CASES = tuple(cases())
