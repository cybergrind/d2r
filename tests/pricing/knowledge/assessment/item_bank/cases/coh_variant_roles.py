"""Reviewed CoH bases and wearer contexts are source-specific, not universal."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.fissure_coh import STATS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Cached guide variant, class, wearer, base, mercenary options, FCR/FHR requirements.
USES = (
    ('echoing-strike-warlock-guide', (2,), 'Warlock', 'merc', 'Archon Plate', ('Act 2 Prayer',), 0, 0),
    ('enchant-sorceress', (1, 2), 'Sorceress', 'merc', 'Archon Plate', ('Act 2 Prayer',), 0, 0),
    ('fissure-druid', (3,), 'Druid', 'player', 'Archon Plate', (), 0, 0),
    ('fissure-druid', (3,), 'Druid', 'merc', 'Archon Plate', ('Act 2 Might',), 0, 0),
    ('fist-of-the-heavens-paladin', (3,), 'Paladin', 'merc', 'Sacred Armor', ('Act 5 Frenzy',), 0, 0),
    ('lightning-fury-amazon-guide', (3,), 'Amazon', 'player', 'Dusk Shroud', (), 0, 0),
    ('lightning-sorceress', (3,), 'Sorceress', 'player', 'Archon Plate', (), 105, 0),
    ('lightning-strike-amazon', (2,), 'Amazon', 'player', 'Archon Plate', (), 0, 0),
    ('meteor-sorceress', (1,), 'Sorceress', 'player', 'Dusk Shroud', (), 63, 60),
    ('mirrored-blades-warlock-guide', (1,), 'Warlock', 'merc', 'Archon Plate', ('Act 2 Might',), 0, 0),
    (
        'nova-sorceress-guide',
        (1, 2, 3),
        'Sorceress',
        'merc',
        'Archon Plate',
        ('Act 2 Might', 'Act 2 Holy Freeze'),
        0,
        0,
    ),
    ('nova-sorceress-guide', (3,), 'Sorceress', 'player', 'Wyrmhide', (), 0, 0),
    ('smite-paladin', (1, 2), 'Paladin', 'player', 'Archon Plate', (), 0, 0),
    ('strafe-amazon', (1, 2), 'Amazon', 'merc', 'Archon Plate', ('Act 2 Might',), 0, 0),
)
RUNES = tuple(SocketItem(name + ' Rune') for name in ('Dol', 'Um', 'Ber', 'Ist'))
COMMON_KEYS = ('127:0', '36:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for build, variants, klass, side, base, mercs, fcr, fhr in USES:
        roles = tuple(f'{build}-{variant}-{side}-chains-honor' for variant in variants)
        configs = tuple(role + '-stats' for role in roles)
        context = {
            'player_class': klass,
            **({'mercenary_type': mercs[0]} if mercs else {}),
            **({'player_total_fcr': fcr} if fcr else {}),
            **({'player_total_fhr': fhr} if fhr else {}),
        }
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Chains of Honor',
                (*STATS, (194, 0, 4)),
                ethereal=side == 'merc',
                sockets=4,
                socket_contents='filled',
                socket_items=RUNES,
                runeword='Chains of Honor',
            )
            examples = [
                ('native', item, context, 'true'),
                ('opposite-ethereal', replace(item, ethereal=side != 'merc'), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        (
                            'other-base',
                            replace(item, base='Archon Plate' if base != 'Archon Plate' else 'Dusk Shroud'),
                            context,
                            'false',
                        ),
                        ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                        (
                            'unread-contents',
                            replace(item, socket_contents='unknown', socket_items=()),
                            context,
                            'unknown',
                        ),
                        (
                            'wrong-count',
                            replace(item, sockets=3, raw_stats=(*STATS, (194, 0, 3)), socket_items=RUNES[:3]),
                            context,
                            'false',
                        ),
                        (
                            'conflicting-count',
                            replace(item, sockets=3, raw_stats=(*STATS, (194, 0, 3))),
                            context,
                            'unknown',
                        ),
                        ('unknown-count', replace(item, sockets=None, raw_stats=STATS), context, 'unknown'),
                        ('unidentified', replace(item, identified=False), context, 'false'),
                        ('wrong-class', item, {**context, 'player_class': 'Assassin'}, 'false'),
                        ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                    )
                )
                if mercs:
                    examples.extend(
                        (
                            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 1 Fire'}, 'false'),
                            (
                                'unknown-merc',
                                item,
                                {k: v for k, v in context.items() if k != 'mercenary_type'},
                                'unknown',
                            ),
                        )
                    )
                    for merc in mercs[1:]:
                        examples.append(('alternative-merc', item, {**context, 'mercenary_type': merc}, 'true'))
                for field, threshold in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
                    if threshold:
                        examples.extend(
                            (
                                (field + '-below', item, {**context, field: threshold - 1}, 'false'),
                                (field + '-unknown', item, {k: v for k, v in context.items() if k != field}, 'unknown'),
                            )
                        )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs))
                                for key in (*COMMON_KEYS, *(('60:0',) if mercs else ()))
                            }
                        )
                    )
                yield Case(
                    id=f'coh-variant/{build}/{side}/{variants[0]}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations={'60:0': configs} if not mercs else {},
                    report_contains=('Chains of Honor', 'Sockets: 4 — Dol, Um, Ber, Ist') if label == 'native' else (),
                    evidence=tuple(f'pricing/data/wp-a-builds.json:/{build}/variants/{v}' for v in variants),
                )


CASES = tuple(cases())
