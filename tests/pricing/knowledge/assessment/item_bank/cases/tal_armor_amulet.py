"""Tal standalone defenses/caster support do not imply companion-set bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ARMOR_USES = {
    'Sorceress': (('blizzard-sorceress', 'Body Armor', 5), ('meteor-sorceress', 'Body Armor', 5)),
    'Warlock': (
        ('echoing-strike-warlock-guide', 'Body Armors', 6),
        ('fire-warlock-guide', 'Body Armors', 8),
        ('mirrored-blades-warlock-guide', 'Body Armors', 4),
    ),
}
AMULET_USES = (
    ('blizzard-sorceress', 'Amulets', 1),
    ('meteor-sorceress', 'Amulets', 1),
    ('nova-sorceress-guide', 'Amulets', 2),
)
AMULET_TABLES = (
    ('fire-wall-sorceress-guide', 30),
    ('frozen-orb-meteor-sorceress', 29),
    ('frozen-orb-sorceress', 29),
    ('hydra-sorceress', 29),
)


def groups():
    for player_class, uses in ARMOR_USES.items():
        yield (
            'armor',
            player_class,
            Item(
                'Lacquered Plate',
                'set',
                "Tal Rasha's Guardianship",
                ((80, 0, 88), (35, 0, 15), (39, 0, 40), (41, 0, 40), (43, 0, 40), (91, 0, -60), (31, 0, 941)),
                complete=True,
            ),
            tuple(g + '-tal-rasha-s-guardianship-tal-player-alternative' for g, _, _ in uses),
            ('80:0', '35:0', '39:0', '41:0', '43:0'),
            ('105:0', '91:0', '31:0'),
            (
                "third-parties/d2data/json/setitems.json:/Tal Rasha's Howling Wind",
                *(f'pricing/data/wp-a-builds.json:/{g}/slots/{slot}/{i}' for g, slot, i in uses),
            ),
        )
    yield (
        'amulet',
        'Sorceress',
        Item(
            'Amulet',
            'set',
            "Tal Rasha's Adjudication",
            ((83, 1, 2), (7, 0, 50 << 8), (9, 0, 42 << 8), (41, 0, 33), (50, 0, 3), (51, 0, 32)),
            complete=True,
        ),
        (
            *(g + '-tal-rasha-s-adjudication-tal-player-alternative' for g, _, _ in AMULET_USES),
            *(g + '-tal-rasha-s-adjudication-caster-gear-alternative' for g, _ in AMULET_TABLES),
        ),
        ('83:1', '7:0', '9:0', '41:0'),
        ('50:0', '51:0', '105:0'),
        (
            "third-parties/d2data/json/setitems.json:/Tal Rasha's Adjudication",
            *(f'pricing/data/wp-a-builds.json:/{g}/slots/{slot}/{i}' for g, slot, i in AMULET_USES),
            *(
                f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{g}.html/sections/{i}'
                for g, i in AMULET_TABLES
            ),
        ),
    )


def cases():
    for slug, player_class, item, roles, keys, irrelevant, evidence in groups():
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class, 'player_items': []}
        examples = [
            ('standalone', item, context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal-impossible', replace(item, ethereal=True), context, 'false'),
            ('ethereal-unknown', replace(item, ethereal=None), context, 'unknown'),
        ]
        if slug == 'armor':
            examples.extend(
                (
                    (
                        'open-socket',
                        replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))),
                        context,
                        'true',
                    ),
                    (
                        'unknown-payload',
                        replace(item, sockets=1, socket_contents='unknown', raw_stats=(*item.raw_stats, (194, 0, 1))),
                        context,
                        'true',
                    ),
                )
            )
        else:
            examples.extend(
                (
                    ('impossible-socket', replace(item, sockets=1), context, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                )
            )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
            yield Case(
                id=f'tal-armor-amulet/{slug}/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=dict.fromkeys(irrelevant, configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else (item.base,),
                report_absent=('10% Faster Cast Rate',),
                evidence=evidence,
            )


CASES = tuple(cases())
