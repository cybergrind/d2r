"""Standalone caster glove/belt alternatives from Hammerdin guide slot tables."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'magefist-caster-progression-alternative',
        'Magefist',
        'unique',
        ('Light Gauntlets', 'Battle Gauntlets', 'Crusader Gauntlets'),
        ((105, 0, 20), (27, 0, 25), (126, 1, 1), (48, 0, 1), (49, 0, 6)),
        ('105:0', '27:0'),
        ('126:1', '48:0', '49:0'),
    ),
    (
        'bloodfist-caster-survival-alternative',
        'Bloodfist',
        'unique',
        ('Heavy Gloves', 'Sharkskin Gloves', 'Vampirebone Gloves'),
        ((99, 0, 30), (7, 0, 40 * 256), (93, 0, 10), (21, 0, 5)),
        ('99:0', '7:0'),
        ('93:0', '21:0'),
    ),
    (
        'immortal-king-s-detail-caster-survival-alternative',
        "Immortal King's Detail",
        'set',
        ('War Belt', 'Colossus Girdle'),
        ((0, 0, 25), (39, 0, 28), (41, 0, 31), (31, 0, 36)),
        ('0:0', '39:0', '41:0'),
        ('99:0', '36:0'),
    ),
    (
        'nightsmoke-equipment-tail-alternative',
        'Nightsmoke',
        'unique',
        ('Belt', 'Mesh Belt', 'Mithril Coil'),
        ((9, 0, 20 * 256), (34, 0, 2), (114, 0, 50), *((s, 0, 10) for s in (39, 41, 43, 45))),
        ('9:0', '34:0', '39:0'),
        (),
    ),
)


def cases():
    context = {'player_class': 'Paladin', 'player_items': []}
    for slug, name, rarity, bases, raw, keys, excluded in SPECS:
        role = 'blessed-hammer-paladin-' + slug
        config = role + '-stats'
        for base in bases:
            item = Item(base, rarity, name, raw)
            for label, candidate, loadout, truth in (
                ('standalone', item, context, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('invalid-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'hammer/gloves-belts/{slug}/{base}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=(name, 'Trade tier:') if truth == 'true' else (base,),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots',
                        'third-parties/d2data/json/uniqueitems.json',
                        'third-parties/d2data/json/setitems.json',
                    ),
                )


CASES = tuple(cases())
