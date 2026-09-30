"""Rare caster Kris: useful skills, optional improvements and uncertain captures."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'abyss-warlock-table-rare-kris'


def cases():
    item = Item('Kriss', 'rare', raw_stats=((83, 7, 1),))
    rows = [
        ('class-minimum', item, {'player_class': 'Warlock'}, 'true', ('83:7',)),
        (
            'abyss-staffmod',
            replace(item, raw_stats=((107, 402, 1),)),
            {'player_class': 'Warlock'},
            'true',
            ('107:402',),
        ),
        (
            'miasma-staffmod',
            replace(item, raw_stats=((107, 399, 1),)),
            {'player_class': 'Warlock'},
            'true',
            ('107:399',),
        ),
        ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'true', ('83:7',)),
        ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'true', ('83:7',)),
        ('wrong-class', item, {'player_class': 'Paladin'}, 'false', ()),
        ('unknown-class', item, {}, 'unknown', ()),
        ('wrong-base', replace(item, base='Dagger'), {'player_class': 'Warlock'}, 'false', ()),
        (
            'no-skills',
            replace(item, raw_stats=((17, 0, 100), (18, 0, 100)), complete=True),
            {'player_class': 'Warlock'},
            'false',
            (),
        ),
        ('unread-skills', replace(item, raw_stats=()), {'player_class': 'Warlock'}, 'unknown', ()),
        (
            'wrong-skill',
            replace(item, raw_stats=((107, 54, 1),), complete=True),
            {'player_class': 'Warlock'},
            'false',
            (),
        ),
        (
            'optional-rolls',
            replace(
                item,
                raw_stats=((83, 7, 2), (39, 0, 21), (0, 0, 10), (80, 0, 30)),
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem('Ist Rune'),),
            ),
            {'player_class': 'Warlock'},
            'true',
            ('83:7', '39:0', '0:0', '80:0'),
        ),
    ]
    for label, candidate, ctx, truth, keys in rows:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for k in keys})
            )
        yield Case(
            id='abyss/rare-kris/' + label,
            item=candidate,
            context=ctx,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            absent_stat_configurations={'17:0': (ROLE + '-stats',), '18:0': (ROLE + '-stats',)},
            evidence=('pricing/data/appraisal-guide-sections.json', 'pricing/raw/mr/planners/gsg0p0l0.json'),
        )


CASES = tuple(cases())
