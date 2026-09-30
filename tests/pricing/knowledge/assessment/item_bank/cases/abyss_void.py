"""Completed Void's legal dagger bases and native low rolls through appraisal."""

from dataclasses import replace
from itertools import product

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'abyss-warlock-build-guide-player-void-weapon-main-alternatives-caster-word-remainder'
RAW = (
    (127, 0, 2),
    (105, 0, 40),
    (357, 0, 10),
    (97, 402, 1),
    (0, 0, 8),
    (1, 0, 8),
    (2, 0, 8),
    (3, 0, 8),
    (80, 0, 30),
    (204, 87 * 64 + 4, 35 << 8),
)


def cases(
    build='abyss-warlock-build-guide',
    player_class='Warlock',
    prefix='abyss',
    keys=('127:0', '105:0', '357:0', '97:402', '80:0'),
    excluded=('204:5572',),
):
    role = build + '-player-void-weapon-main-alternatives-caster-word-remainder'
    for base, quality in product(
        ('Kriss', 'Blade', 'Cinquedeas', 'Stilleto', 'Fanged Knife', 'Legend Spike'),
        ('normal', 'superior', 'low_quality'),
    ):
        item = Item(base, quality, 'Void', RAW, sockets=3, socket_contents='filled', runeword='Void')
        for label, candidate, ctx, truth in (
            ('low-roll', item, {'player_class': player_class}, 'true'),
            ('ethereal', replace(item, ethereal=True), {'player_class': player_class}, 'true'),
            ('unknown-sockets', replace(item, sockets=None), {'player_class': player_class}, 'unknown'),
            ('empty-base', replace(item, socket_contents='empty'), {'player_class': player_class}, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                    )
                )
            yield Case(
                id=f'{prefix}/void/{base}/{quality}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(excluded, (role + '-stats',)),
                report_contains=('Void',),
                evidence=('third-parties/d2data/json/runes.json:/Void',),
            )


CASES = tuple(cases())
