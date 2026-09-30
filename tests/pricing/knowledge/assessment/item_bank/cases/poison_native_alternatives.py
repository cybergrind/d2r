"""Poison Nova alternatives retain base staffmods and poison-specific armor rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


WHITE_ROLE = 'poison-nova-white-alternative'
BRAMBLE_ROLE = 'poison-nova-necromancer-player-bramble-body-armor-main-alternatives-support-word-alternative'
# Independent native recipe and socket contributions; only observed stats are supplied.
WHITE = (
    (107, 92, 2),
    (188, 17, 3),
    (35, 0, 4),
    (105, 0, 20),
    (9, 0, 13 * 256),
    (107, 68, 3),
    (107, 84, 2),
    (107, 69, 4),
    (3, 0, 10),
    (194, 0, 2),
)
BARBS = (246 << 6) | 13
BRAMBLE = (
    (332, 0, 25),
    (99, 0, 50),
    (31, 0, 700),
    (151, 103, 15),
    (86, 0, 13),
    (45, 0, 100),
    (39, 0, 30),
    (44, 0, 5),
    (77, 0, 5),
    (27, 0, 15),
    (204, BARBS, (33 << 8) | 33),
    (194, 0, 4),
)


def cases():
    context = {'player_class': 'Necromancer'}
    for name, role, base, raw, runes, keys, excluded, locator in (
        (
            'White',
            WHITE_ROLE,
            'Bone Wand',
            WHITE,
            ('Dol Rune', 'Io Rune'),
            ('107:92', '188:17', '35:0', '105:0', '9:0', '107:68'),
            ('107:84', '107:69'),
            '/poison-nova-necromancer/slots/Weapon/3',
        ),
        (
            'Bramble',
            BRAMBLE_ROLE,
            'Dusk Shroud',
            BRAMBLE,
            ('Ral Rune', 'Ohm Rune', 'Sur Rune', 'Eth Rune'),
            ('332:0', '99:0', '31:0', '86:0', '45:0', '39:0', '44:0', '77:0', '27:0'),
            ('151:103', f'204:{BARBS}'),
            '/poison-nova-necromancer/slots/Body Armor/1',
        ),
    ):
        config = role + '-stats'
        qualities = ('normal', 'superior') if name == 'White' else ('normal', 'superior', 'low_quality')
        for quality in qualities:
            original = NativeRunewordItem(
                base,
                quality,
                name,
                raw,
                sockets=len(runes),
                socket_contents='filled',
                runeword=name,
                socket_items=tuple(SocketItem(r) for r in runes),
            )
            if name == 'Bramble' and quality == 'low_quality':
                original = replace(original, raw_stats=tuple((s, p, 600 if s == 31 else v) for s, p, v in raw))
            variants = [
                ('minimum', original, context, 'true'),
                ('wrong-class', original, {'player_class': 'Druid'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                ('ethereal', replace(original, ethereal=True), context, 'true' if name == 'White' else 'false'),
            ]
            if name == 'White':
                for label, bonus, truth in [('perfect-staffmod', 3, 'true'), ('insufficient-staffmod', 1, 'false')]:
                    variants.append(
                        (
                            label,
                            replace(
                                original,
                                raw_stats=tuple((s, p, bonus if (s, p) == (107, 92) else v) for s, p, v in raw),
                            ),
                            context,
                            truth,
                        )
                    )
                missing = tuple(row for row in raw if row[:2] != (107, 92))
                variants.extend(
                    [
                        ('unread-staffmod', replace(original, raw_stats=missing), context, 'unknown'),
                        # This role deliberately requires observed staffmod evidence.
                        (
                            'complete-without-staffmod',
                            replace(original, raw_stats=missing, complete=True),
                            context,
                            'unknown',
                        ),
                        ('elite-base', replace(original, base='Lich Wand'), context, 'true'),
                    ]
                )
            else:
                variants.extend(
                    [
                        (
                            'maximum-rolls',
                            replace(
                                original,
                                raw_stats=tuple(
                                    (s, p, 50 if s == 332 else 21 if s == 151 else v) for s, p, v in original.raw_stats
                                ),
                            ),
                            context,
                            'true',
                        ),
                        (
                            'exhausted-charges',
                            replace(
                                original,
                                raw_stats=tuple((s, p, 33 << 8 if s == 204 else v) for s, p, v in original.raw_stats),
                            ),
                            context,
                            'true',
                        ),
                        (
                            'different-base',
                            replace(
                                original,
                                base='Archon Plate',
                                raw_stats=tuple(
                                    (s, p, (650 if quality == 'low_quality' else 800) if s == 31 else v)
                                    for s, p, v in original.raw_stats
                                ),
                            ),
                            context,
                            'true',
                        ),
                    ]
                )
            for label, specimen, ctx, truth in variants:
                active = truth == 'true'
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'poison-native-alternatives/{name}/{quality}/{label}',
                    item=specimen,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=(name, 'Sockets: 2 — Dol, Io', 'Poison Nova', 'staffmod range: 1-3')
                    if name == 'White' and active
                    else (name, 'Sockets: 4 — Ral, Ohm, Sur, Eth', '(25-50%)', '(15-21)')
                    if name == 'Bramble' and active
                    else (),
                    detail_contains=('Thorns and Spirit of Barbs do not multiply poison damage;',)
                    if name == 'Bramble' and label == 'minimum'
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:{locator}',
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )


CASES = tuple(cases())
