"""Specialist attack alternatives highlight effects the actual skill can use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GNASHER = Item(
    'Hand Axe',
    'unique',
    'The Gnasher',
    ((0, 0, 8), (135, 0, 50), (136, 0, 20), (17, 0, 60), (18, 0, 60)),
    named_table_id=0,
)
TWITCHTHROE = Item(
    'Studded Leather',
    'unique',
    'Twitchthroe',
    ((93, 0, 20), (2, 0, 10), (20, 0, 25), (0, 0, 10), (99, 0, 20)),
    named_table_id=82,
)


def cases():
    for original, role, klass, bases, keys, excluded, locator in (
        (
            GNASHER,
            'smite-paladin-gnasher-weapon-utility-alternative',
            'Paladin',
            ('Hatchet', 'Tomahawk'),
            ('136:0', '135:0', '0:0'),
            ('17:0', '18:0'),
            '/smite-paladin/slots/Weapon/7',
        ),
        (
            TWITCHTHROE,
            'strafe-amazon-twitchthroe-body-armor-utility-alternative',
            'Amazon',
            ('Trellised Armor', 'Wire Fleece'),
            ('93:0', '99:0', '0:0', '2:0'),
            ('20:0',),
            '/strafe-amazon/slots/Body Armor/8',
        ),
    ):
        config = role + '-stats'
        context = {'player_class': klass}
        variants = [
            ('native', original, context, 'true'),
            ('exceptional', replace(original, base=bases[0]), context, 'true'),
            ('elite', replace(original, base=bases[1]), context, 'true'),
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('wrong-class', original, {'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            (
                'open-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
        ]
        if original is GNASHER:
            variants.append(
                (
                    'maximum-ed-still-not-smite-damage',
                    replace(
                        original, raw_stats=tuple((s, p, 70 if s in (17, 18) else v) for s, p, v in original.raw_stats)
                    ),
                    context,
                    'true',
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'specialist-attack-uniques/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(original.name, 'Trade tier:') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    f'third-parties/d2data/json/uniqueitems.json:/{original.named_table_id}',
                ),
            )


CASES = tuple(cases())
