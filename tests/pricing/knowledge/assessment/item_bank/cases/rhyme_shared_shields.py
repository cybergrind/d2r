"""Rhyme recipe utility across exact Bone Shield and generic caster alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.rhyme_class_shields import NATIVE
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


EXACT = (
    ('sorceress', 'Sorceress', ('blizzard-sorceress', 'lightning-sorceress', 'meteor-sorceress')),
    ('assassin', 'Assassin', ('fire-blast-assassin', 'lightning-sentry-assassin', 'wake-of-fire-assassin')),
    ('amazon', 'Amazon', ('lightning-fury-amazon-guide', 'lightning-strike-amazon')),
)
GENERIC = (
    (
        'sorceress',
        'Sorceress',
        tuple(
            (g, s, n)
            for g, n in (
                ('fire-wall-sorceress-guide', 30),
                ('hydra-sorceress', 29),
            )
            for s in ('off-hand', 'off-hand-swap')
        ),
    ),
    (
        'frozen-sorceress',
        'Sorceress',
        tuple(
            (g, s, 29)
            for g in ('frozen-orb-sorceress', 'frozen-orb-meteor-sorceress')
            for s in ('off-hand', 'off-hand-swap')
        ),
    ),
    ('warlock', 'Warlock', (('blood-boil-warlock-guide', 'off-hand', 29), ('summoner-warlock-guide', 'off-hand', 29))),
    ('necromancer', 'Necromancer', (('summoner-necromancer-guide', 'off-hand', 33),)),
)
GROUPS = tuple(
    (
        f'exact-{g}',
        c,
        True,
        tuple(f'{b}-0-rhyme' for b in builds),
        tuple(f'pricing/data/wp-a-builds.json:/{b}/variants/0' for b in builds),
    )
    for g, c, builds in EXACT
) + tuple(
    (
        f'generic-{g}',
        c,
        False,
        tuple(f'{b}-{slot}-rhyme-caster-gear' for b, slot, _ in uses),
        tuple(
            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{b}.html/sections/{n}'
            for b, _, n in uses
        ),
    )
    for g, c, uses in GENERIC
)
RUNES = (SocketItem('Shael Rune'), SocketItem('Eth Rune'))


def cases():
    for group, klass, exact, roles, sources in GROUPS:
        base_exact = exact or group == 'generic-frozen-sorceress'
        configs = tuple(role + '-stats' for role in roles)
        grades = dict.fromkeys(('153:0', '80:0', '39:0', '41:0', '43:0', '45:0'), 'desirable')
        grades.update(dict.fromkeys(('102:0', '20:0'), 'supporting'))
        if not exact:
            grades.update(dict.fromkeys(('153:0', '79:0', '27:0'), 'supporting'))
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = NativeRunewordItem(
                'Bone Shield',
                quality,
                'Rhyme',
                (*NATIVE, (20, 0, 40)),
                sockets=2,
                socket_contents='filled',
                socket_items=RUNES,
                runeword='Rhyme',
            )
            examples = [
                ('native', item, context, 'true'),
                ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        ('ethereal', replace(item, ethereal=True), context, 'false'),
                        ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                        ('reversed-runes', replace(item, socket_items=RUNES[::-1]), context, None),
                        ('empty', replace(item, socket_items=(), socket_contents='empty'), context, None),
                        ('unidentified', replace(item, identified=False), context, None),
                        (
                            'unknown-sockets',
                            observation(
                                item,
                                sockets=None,
                                socket_items=(),
                                socket_contents='unknown',
                                raw_stats=tuple(s for s in item.raw_stats if s[0] != 194),
                            ),
                            context,
                            'unknown',
                        ),
                        (
                            'small-shield',
                            replace(
                                item,
                                base='Small Shield',
                                raw_stats=tuple((s, p, 25 if s == 20 else v) for s, p, v in item.raw_stats),
                            ),
                            context,
                            'false' if base_exact else 'true',
                        ),
                        (
                            'uncaptured-mf',
                            replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 80)),
                            context,
                            'true',
                        ),
                    )
                )
            for label, candidate, loadout, truth in examples:
                filtered = group == 'generic-frozen-sorceress' and label == 'small-shield'
                active = truth == 'true'
                captured = {f'{s}:{p}' for s, p, _ in candidate.raw_stats}
                expected = {}
                if truth is not None and not filtered:
                    expected['roles'] = Contains(
                        *(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles)
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        *(IsPartialDict(configuration_id=c, desirability=grade) for c in configs)
                                    )
                                )
                                for key, grade in grades.items()
                                if key in captured
                            }
                        )
                    )
                absent = {'105:0': configs, '127:0': configs}
                if exact:
                    absent.update(dict.fromkeys(('79:0', '27:0'), configs))
                if label == 'uncaptured-mf':
                    absent['80:0'] = configs
                yield Case(
                    id=f'rhyme-shared/{group}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else configs,
                    absent_roles=roles if filtered else (),
                    absent_stat_configurations=absent,
                    report_contains=(
                        'Rhyme',
                        'Sockets: 2 — Shael, Eth',
                        'Cannot Be Frozen',
                        '40% Faster Block Rate',
                        '25% Better Chance of Getting Magic Items',
                    )
                    if label == 'native'
                    else (),
                    report_absent=('25% Better Chance of Getting Magic Items',) if label == 'uncaptured-mf' else (),
                    evidence=('third-parties/d2data/json/runes.json:/Rhyme', *sources),
                )


CASES = tuple(cases())
