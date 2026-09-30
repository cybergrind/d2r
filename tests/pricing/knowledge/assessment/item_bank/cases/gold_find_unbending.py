"""Gold Find's cited Phase Blade preserves combat benefits and Berserk leech limits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'gold-find-barbarian-unbending-will-phase-blade-combat-word-alternative'
CONFIG = ROLE + '-stats'
RUNES = tuple(SocketItem(name + ' Rune') for name in ('Fal', 'Io', 'Ith', 'Eld', 'El', 'Hel'))


def sword(quality, ed=300, ias=20, leech=8):
    return Item(
        'Phase Blade',
        quality,
        'Unbending Will',
        (
            (17, 0, ed),
            (18, 0, ed),
            (93, 0, ias),
            (188, 32, 3),
            (0, 0, 10),
            (3, 0, 10),
            (34, 0, 8),
            (60, 0, leech),
            (117, 0, 1),
            (198, 8786, 18),
            (194, 0, 6),
            (19, 0, 50),
            (122, 0, 75),
            (124, 0, 50),
            (91, 0, -20),
        ),
        sockets=6,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Unbending Will',
    )


def cases():
    context = {'player_class': 'Barbarian'}
    for quality in ('normal', 'superior', 'low_quality'):
        original = sword(quality)
        rows = [
            (f'rolls-{ed}-{ias}-{leech}', sword(quality, ed, ias, leech), context, 'true')
            for ed in (300, 350)
            for ias in (20, 30)
            for leech in (8, 10)
        ]
        rows += [
            ('different-legal-base', replace(original, base='Crystal Sword'), context, 'absent'),
            ('wrong-class', original, {'player_class': 'Paladin'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('empty', replace(original, socket_contents='empty', socket_items=()), context, 'false'),
            ('unknown-contents', replace(original, socket_contents='unknown', socket_items=()), context, 'unknown'),
            (
                'unknown-count',
                replace(
                    original,
                    sockets=None,
                    socket_contents='unknown',
                    socket_items=(),
                    raw_stats=tuple(s for s in original.raw_stats if s[0] != 194),
                ),
                context,
                'unknown',
            ),
            ('missing-word', replace(original, name=None, runeword=None), context, 'absent'),
            ('uncaptured-stats', replace(original, raw_stats=((194, 0, 6),)), context, 'true'),
        ]
        for label, item, loadout, truth in rows:
            expected = (
                {}
                if truth == 'absent'
                else {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            )
            active = truth == 'true' and label != 'uncaptured-stats'
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability='desirable')
                                )
                            )
                            for key in ('17:0', '18:0', '93:0', '188:32', '0:0', '3:0', '34:0')
                        }
                    )
                )
            yield Case(
                id=f'gold-find-unbending/{quality}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario='positive'
                if active
                else 'unknown'
                if truth == 'unknown' or label == 'uncaptured-stats'
                else 'negative',
                absent_roles=(ROLE,) if truth == 'absent' else (),
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(('60:0', '198:8786'), (CONFIG,)),
                report_contains=('Unbending Will', 'Sockets: 6', 'Fal, Io, Ith, Eld, El, Hel', 'Taunt')
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/gold-find-barbarian/slots/Weapon/2',
                    'third-parties/d2data/json/runes.json:/Unbending Will',
                ),
            )


CASES = tuple(cases())
