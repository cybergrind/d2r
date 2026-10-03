"""Preparation shields and completed four-filler setups are separate uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


BASE = Item(
    'Sacred Targe',
    'magic',
    raw_stats=((20, 0, 50), (102, 0, 30), (39, 0, 27), (41, 0, 27), (43, 0, 27), (45, 0, 27)),
    sockets=4,
)
RUBY = SocketItem('Jewel', ((17, 0, 31), (18, 0, 31), (93, 0, 15)), complete=True)


def cases():
    result = []
    for slug, span, bonus, children, extra in (
        ('ruby', 73, ((17, 0, 124), (18, 0, 124), (93, 0, 60)), (RUBY,) * 4, ('17:0', '18:0', '93:0')),
        ('ist', 75, ((80, 0, 100),), (SocketItem('Ist Rune'),) * 4, ('80:0',)),
    ):
        for state in ('empty', 'filled'):
            role = f'zeal-paladin-specialist-shield-{slug}-{state}'
            item = (
                BASE
                if state == 'empty'
                else replace(BASE, raw_stats=(*BASE.raw_stats, *bonus), socket_contents='filled', socket_items=children)
            )
            rows = [
                ('positive', 'candidate', item, {'player_class': 'Paladin'}),
                ('negative', 'wrong-class', item, {'player_class': 'Sorceress'}),
                (
                    'negative',
                    'insufficient-bonus',
                    replace(item, raw_stats=((20, 0, 49), *item.raw_stats[1:])),
                    {'player_class': 'Paladin'},
                ),
                ('unknown', 'unknown-class', item, {}),
            ]
            if state == 'filled':
                rows.extend(
                    [
                        (
                            'negative',
                            'wrong-fourth-filler',
                            replace(item, socket_items=(*children[:3], SocketItem('El Rune'))),
                            {'player_class': 'Paladin'},
                        ),
                        ('unknown', 'unread-children', replace(item, socket_items=()), {'player_class': 'Paladin'}),
                    ]
                )
            else:
                rows.extend(
                    [
                        ('negative', 'only-three-sockets', replace(item, sockets=3), {'player_class': 'Paladin'}),
                        ('unknown', 'unread-sockets', replace(item, sockets=None), {'player_class': 'Paladin'}),
                    ]
                )
            for scenario, label, observed, context in rows:
                expected = {'roles': Contains(IsPartialDict(id=role))}
                if slug == 'ist' and state == 'filled' and label in ('candidate', 'wrong-fourth-filler'):
                    expected['roles'] = Contains(
                        IsPartialDict(id=role, status='partial' if scenario == 'positive' else 'failed')
                    )
                if scenario == 'positive':
                    keys = ('20:0', '102:0') + (extra if state == 'filled' else ())
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                result.append(
                    Case(
                        id=f'zeal/specialist-shields/{slug}/{state}/{label}',
                        item=observed,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        report_contains=('Sacred Targe',),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
