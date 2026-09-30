"""Fortitude physical damage belongs to the specified wearer and native armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    ('double-throw-barbarian-guide', (1,), 'Barbarian', 'player', 'Archon Plate', ()),
    ('fire-blast-assassin', (1,), 'Assassin', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('fire-warlock-guide', (1, 2), 'Warlock', 'merc', 'Archon Plate', ('Act 2 Might',)),
    ('fist-of-the-heavens-paladin', (2,), 'Paladin', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('lightning-fury-amazon-guide', (1, 2), 'Amazon', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('lightning-sentry-assassin', (1, 2), 'Assassin', 'merc', 'Sacred Armor', ('Act 2 Holy Freeze',)),
    ('lightning-sorceress', (1, 2), 'Sorceress', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('meteor-sorceress', (1, 3), 'Sorceress', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('poison-nova-necromancer', (1, 2), 'Necromancer', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('strafe-amazon', (1, 2), 'Amazon', 'player', 'Archon Plate', ()),
    ('wake-of-fire-assassin', (1,), 'Assassin', 'merc', 'Sacred Armor', ('Act 2 Might',)),
    ('fissure-druid', (1, 2), 'Druid', 'merc', 'Sacred Armor', ('Act 2 Might', 'Act 2 Holy Freeze')),
    ('zeal-paladin', (), 'Paladin', 'merc', 'Sacred Armor', ('Act 2 Might',)),
)
STATS = (
    (17, 0, 300),
    (18, 0, 300),
    (16, 0, 200),
    (105, 0, 25),
    (194, 0, 4),
    (201, 3855, 20),
    (216, 0, 8 * 256),
    (34, 0, 7),
    (74, 0, 7),
    (42, 0, 5),
    *((sid, 0, 25) for sid in (39, 41, 43, 45)),
)
RUNES = tuple(SocketItem(name + ' Rune') for name in ('El', 'Sol', 'Dol', 'Lo'))
KEYS = ('17:0', '18:0', '16:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for build, variants, klass, side, base, mercs in USES:
        roles = (
            tuple(f'{build}-{v}-{side}-fortitude' for v in variants)
            if variants
            else ('zeal-paladin-merc-word-fortitude-end',)
        )
        configs = tuple(r + '-stats' for r in roles)
        keys = (*KEYS, *(('201:3855', '216:0', '34:0', '74:0', '42:0') if not variants else ()))
        context = {'player_class': klass, **({'mercenary_type': mercs[0]} if mercs else {})}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Fortitude',
                STATS,
                ethereal=side == 'merc',
                sockets=4,
                socket_contents='filled',
                socket_items=RUNES,
                runeword='Fortitude',
            )
            examples = [
                ('native-minimum', item, context, 'true'),
                ('opposite-ethereal', replace(item, ethereal=side != 'merc'), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        (
                            'maximum-rolls',
                            replace(
                                item,
                                raw_stats=tuple(
                                    (sid, layer, 30 if sid in (39, 41, 43, 45) else 12 * 256 if sid == 216 else value)
                                    for sid, layer, value in STATS
                                ),
                            ),
                            context,
                            'true',
                        ),
                        (
                            'other-base',
                            replace(item, base='Archon Plate' if base == 'Sacred Armor' else 'Sacred Armor'),
                            context,
                            'false',
                        ),
                        ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                        (
                            'unknown-contents',
                            replace(item, socket_contents='unknown', socket_items=()),
                            context,
                            'unknown',
                        ),
                        (
                            'wrong-class',
                            item,
                            {**context, 'player_class': 'Druid' if klass != 'Druid' else 'Barbarian'},
                            'false',
                        ),
                        ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                        ('unidentified', replace(item, identified=False), context, 'false'),
                        (
                            'wrong-count',
                            replace(
                                item,
                                sockets=3,
                                socket_items=RUNES[:3],
                                raw_stats=tuple(
                                    (sid, layer, 3 if sid == 194 else value) for sid, layer, value in STATS
                                ),
                            ),
                            context,
                            'false',
                        ),
                        (
                            'unknown-count',
                            replace(item, sockets=None, raw_stats=tuple(r for r in STATS if r[0] != 194)),
                            context,
                            'unknown',
                        ),
                    )
                )
                if mercs:
                    examples.extend(
                        (
                            ('caster-merc', item, {**context, 'mercenary_type': 'Act 3 Fire'}, 'false'),
                            ('unknown-merc', item, {'player_class': klass}, 'unknown'),
                        )
                    )
                    for merc in mercs[1:]:
                        examples.append(('alternative-merc', item, {**context, 'mercenary_type': merc}, 'true'))
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if not variants and label == 'other-base':
                    # The Zeal profile filters base identity before predicates.
                    # Its configurations must remain absent, as asserted below.
                    expected = {}
                if label in ('native-minimum', 'maximum-rolls'):
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict({'216:0': IsPartialDict(value=120 if label == 'maximum-rolls' else 80)})
                    )
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(*configs)) for k in keys}
                        )
                    )
                sources = (
                    tuple(f'pricing/data/wp-a-builds.json:/{build}/variants/{v}' for v in variants)
                    if variants
                    else (
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/225',
                    )
                )
                yield Case(
                    id=f'fortitude-variant/{build}/{side}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations={'105:0': configs},
                    report_contains=('Fortitude', 'Sockets: 4 — El, Sol, Dol, Lo', '300% Enhanced Damage')
                    if label == 'native-minimum'
                    else (),
                    evidence=(*sources, 'third-parties/d2data/json/runes.json:/Fortitude'),
                )


CASES = tuple(cases())
