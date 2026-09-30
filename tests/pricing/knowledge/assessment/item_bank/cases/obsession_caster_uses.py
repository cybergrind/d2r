"""Obsession casting components: independent rolls and source-specific staff bases."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


MAIN = '-player-obsession-weapon-main-alternatives-caster-word-remainder'
GEAR = '-obsession-caster-recipe-gear'
USES = (
    (
        'Warlock',
        False,
        (
            (
                'echoing-strike-warlock-guide',
                MAIN,
                'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/4',
            ),
            ('fire-warlock-guide', MAIN, 'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Weapon/0'),
            ('blood-boil-warlock-guide', GEAR, 29),
            ('summoner-warlock-guide', GEAR, 29),
        ),
    ),
    (
        'Sorceress',
        False,
        (('lightning-sorceress', MAIN, 'pricing/data/wp-a-builds.json:/lightning-sorceress/slots/Weapon/6'),),
    ),
    (
        'Sorceress',
        True,
        (
            ('frozen-orb-sorceress', GEAR, 29),
            ('frozen-orb-meteor-sorceress', GEAR, 29),
            ('fire-wall-sorceress-guide', GEAR, 30),
            ('hydra-sorceress', GEAR, 29),
        ),
    ),
)
RUNES = tuple(SocketItem(n + ' Rune') for n in ('Zod', 'Ist', 'Lem', 'Lum', 'Io', 'Nef'))
RANGES = ((39, 60, 70), (41, 60, 70), (43, 60, 70), (45, 60, 70), (76, 15, 25), (27, 15, 30))
KEYS = ('127:0', '105:0', '99:0', '39:0', '41:0', '43:0', '45:0', '76:0', '27:0', '80:0', '79:0', '1:0', '3:0')


def obsession(quality, perfect=()):
    return NativeRunewordItem(
        'Archon Staff',
        quality,
        'Obsession',
        (
            (194, 0, 6),
            (127, 0, 4),
            (105, 0, 65),
            (99, 0, 60),
            *((sid, 0, high if sid in perfect else low) for sid, low, high in RANGES),
            (80, 0, 30),
            (79, 0, 75),
            (1, 0, 10),
            (3, 0, 10),
            (152, 0, 1),
            (81, 0, 1),
            (201, 72 * 64 + 10, 24),
        ),
        sockets=6,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Obsession',
        complete=True,
    )


def cases():
    for klass, exact, sources in USES:
        roles = tuple(g + suffix for g, suffix, _ in sources)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = obsession(quality)
            examples = [
                ('minimum', item, context, 'true', ()),
                (
                    'maximum',
                    obsession(quality, tuple(s[0] for s in RANGES)),
                    context,
                    'true',
                    tuple(s[0] for s in RANGES),
                ),
                ('life-only-perfect', obsession(quality, (76,)), context, 'true', (76,)),
                ('res-only-perfect', obsession(quality, (39, 41, 43, 45)), context, 'true', (39, 41, 43, 45)),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false', ()),
                ('unknown-class', item, {}, 'unknown', ()),
                ('ethereal', replace(item, ethereal=True), context, 'true', ()),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'true', ()),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false', ()),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false', ()),
                ('unidentified', replace(item, identified=False), context, 'false', ()),
                ('war-staff', replace(item, base='War Staff'), context, 'false' if exact else 'true', ()),
            ]
            for label, candidate, loadout, truth, perfect in examples:
                bad_identity = label in ('wrong-recipe', 'empty', 'unidentified')
                assessment = (
                    {}
                    if bad_identity or (label == 'war-staff' and exact)
                    else {
                        'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                    }
                )
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in KEYS}
                        )
                    )
                expected = {'assessment': IsPartialDict(**assessment)}
                if bad_identity:
                    expected['extraction'] = IsPartialDict(item=IsPartialDict(runeword=None))
                elif label in ('minimum', 'maximum', 'life-only-perfect', 'res-only-perfect'):
                    expected['extraction'] = IsPartialDict(
                        item=IsPartialDict(runeword='Obsession'),
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=sid),
                                    roll_range=IsPartialDict(min=low, max=high),
                                    roll_quality='perfect' if sid in perfect else 'low',
                                )
                                for sid, low, high in RANGES
                            )
                        ),
                    )
                yield Case(
                    id=f'obsession-caster/{klass}/{exact}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected=expected,
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations=dict.fromkeys(('81:0', f'201:{72 * 64 + 10}'), configs),
                    report_contains=('Obsession', 'Sockets: 6 — Zod, Ist, Lem, Lum, Io, Nef')
                    if label == 'minimum'
                    else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Obsession',
                        *(
                            location
                            if isinstance(location, str)
                            else 'pricing/data/appraisal-guide-sections.json:/sources/'
                            f'pricing~1raw~1mr~1guides__{g}.html/sections/{location}'
                            for g, _, location in sources
                        ),
                    ),
                )


CASES = tuple(cases())
