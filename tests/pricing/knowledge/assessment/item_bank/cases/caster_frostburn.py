"""Frostburn mana utility across three caster alternatives and both upgrades."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BUILDS = ('enchant-sorceress', 'lightning-sorceress', 'nova-sorceress-guide')
ROLES = tuple(build + '-frostburn-find-absorb-alternative' for build in BUILDS)
CONFIGS = tuple(role + '-stats' for role in ROLES)
RAW = ((77, 0, 40), (17, 0, 5), (18, 0, 5), (54, 0, 1), (55, 0, 6), (56, 0, 50))


def cases():
    context = {'player_class': 'Sorceress'}
    for base in ('Gauntlets', 'War Gauntlets', 'Ogre Gauntlets'):
        original = Item(base, 'unique', 'Frostburn', (*RAW, (16, 0, 10)), named_table_id=106)
        rows = [
            ('minimum-defense', original, context, 'true'),
            ('perfect-defense', replace(original, raw_stats=(*RAW, (16, 0, 20))), context, 'true'),
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('wrong-class', original, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            (
                'unread-mana',
                replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != 77)),
                context,
                'true',
            ),
            ('unread-stats', replace(original, raw_stats=()), context, 'true'),
            (
                'invalid-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'false',
            ),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ]
        for label, item, loadout, truth in rows:
            active = truth == 'true'
            mana = any(s[0] == 77 for s in item.raw_stats)
            assessment = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
            }
            if active and mana:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            '77:0': IsPartialDict(
                                contributions=Contains(
                                    *(
                                        IsPartialDict(
                                            configuration_id=role + '-stats', role_id=role, desirability='desirable'
                                        )
                                        for role in ROLES
                                    )
                                )
                            )
                        }
                    )
                )
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            if label in ('minimum-defense', 'perfect-defense'):
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat={'id': 16, 'layer': 0, 'raw': 20 if label == 'perfect-defense' else 10},
                            roll_quality='perfect' if label == 'perfect-defense' else 'low',
                        )
                    )
                )
            yield Case(
                id=f'caster-frostburn/{base}/{label}',
                item=item,
                context=loadout,
                expected=expected,
                covers=ROLES,
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else CONFIGS,
                absent_stat_configurations=dict.fromkeys(
                    ('16:0', '17:0', '18:0', '54:0', '55:0', '56:0', *(('77:0',) if not mana else ())), CONFIGS
                ),
                report_contains=(
                    ('Frostburn', 'Trade tier:')
                    if item.identified and item.ethereal is False and item.sockets == 0
                    else ()
                )
                + (('Increase Maximum Mana 40%',) if item.identified and mana else ())
                + (('(10-20%) Enhanced Defense',) if label in ('minimum-defense', 'perfect-defense') else ()),
                detail_contains=(
                    'Compare total mana and the casting breakpoint lost when replacing Faster Cast Rate gloves',
                )
                if active
                else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/106',
                    *(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Gloves/{2 if build == BUILDS[2] else 3}'
                        for build in BUILDS
                    ),
                ),
            )


CASES = tuple(cases())
