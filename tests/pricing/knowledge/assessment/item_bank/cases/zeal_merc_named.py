"""Later Zeal mercenary gear: explicit fillers and native low rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


RES = tuple((s, 0, 15) for s in (39, 41, 43, 45))
IAS = SocketItem('Jewel', ((93, 0, 15),), complete=True)
SCINT = SocketItem('Jewel', ((93, 0, 15), *((s, 0, 11) for s in (39, 41, 43, 45))), complete=True)
GUILLAUME = Item(
    'Winged Helm', 'set', "Guillaume's Face", ((16, 0, 120), (99, 0, 30), (136, 0, 35), (141, 0, 15), (0, 0, 15))
)
GAZE = Item(
    'Grim Helm',
    'unique',
    'Vampire Gaze',
    ((60, 0, 6), (62, 0, 6), (36, 0, 15), (35, 0, 10), (16, 0, 100), (54, 0, 6), (55, 0, 22)),
)
EXAMPLES = (
    (
        'shaftstop-um',
        221,
        Item('Mesh Armor', 'unique', 'Shaftstop', ((16, 0, 180), (36, 0, 30), (7, 0, 60 * 256), (32, 0, 250), *RES)),
        SocketItem('Um Rune'),
        ('36:0', '7:0', '39:0', '45:0'),
        (),
        'Boneweave',
    ),
    (
        'duriel-um',
        223,
        Item(
            'Cuirass',
            'unique',
            "Duriel's Shell",
            (
                (16, 0, 160),
                (0, 0, 15),
                (214, 0, 10),
                (216, 0, 8 * 256),
                (153, 0, 1),
                (39, 0, 35),
                (41, 0, 35),
                (43, 0, 65),
                (45, 0, 35),
            ),
        ),
        SocketItem('Um Rune'),
        ('153:0', '0:0', '216:0', '39:0', '43:0'),
        (),
        'Great Hauberk',
    ),
    (
        'tal-amethyst',
        236,
        Item(
            'Death Mask',
            'set',
            "Tal Rasha's Horadric Crest",
            ((60, 0, 10), (62, 0, 10), (7, 0, 60 * 256), (9, 0, 30 * 256), (0, 0, 10), *RES),
        ),
        SocketItem('Perfect Amethyst'),
        ('60:0', '7:0', '0:0', '39:0', '45:0'),
        ('62:0', '9:0'),
        'Demonhead',
    ),
    (
        'guillaume-ias',
        237,
        replace(GUILLAUME, raw_stats=(*GUILLAUME.raw_stats, (93, 0, 15))),
        IAS,
        ('136:0', '141:0', '99:0', '0:0', '93:0'),
        (),
        'Spired Helm',
    ),
    (
        'gaze-ias',
        238,
        replace(GAZE, raw_stats=(*GAZE.raw_stats, (93, 0, 15))),
        IAS,
        ('60:0', '36:0', '35:0', '93:0'),
        ('62:0',),
        'Bone Visage',
    ),
    (
        'stealskull-ias',
        239,
        Item(
            'Casque',
            'unique',
            'Stealskull',
            ((60, 0, 5), (62, 0, 5), (99, 0, 10), (93, 0, 25), (80, 0, 30), (16, 0, 200)),
        ),
        IAS,
        ('60:0', '99:0', '93:0', '80:0'),
        ('62:0',),
        'Armet',
    ),
    (
        'kira-ral',
        240,
        Item(
            'Tiara',
            'unique',
            "Kira's Guardian",
            ((31, 0, 50), (39, 0, 80), (41, 0, 50), (43, 0, 50), (45, 0, 50), (153, 0, 1), (99, 0, 20)),
        ),
        SocketItem('Ral Rune'),
        ('39:0', '41:0', '43:0', '45:0', '153:0', '99:0'),
        (),
        'Diadem',
    ),
    (
        'guillaume-cham',
        242,
        replace(GUILLAUME, raw_stats=(*GUILLAUME.raw_stats, (153, 0, 1))),
        SocketItem('Cham Rune'),
        ('136:0', '141:0', '99:0', '0:0', '153:0'),
        (),
        'Spired Helm',
    ),
    (
        'gaze-scintillating',
        244,
        replace(GAZE, ethereal=True, raw_stats=(*GAZE.raw_stats, (93, 0, 15), *((s, 0, 11) for s in (39, 41, 43, 45)))),
        SCINT,
        ('60:0', '36:0', '35:0', '93:0', '39:0', '41:0', '43:0', '45:0'),
        ('62:0',),
        'Bone Visage',
    ),
)
MIGHT = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}


def cases():
    result = []
    for slug, span, base, filler, keys, irrelevant, upgrade in EXAMPLES:
        role = 'zeal-paladin-later-merc-' + slug
        item = replace(base, sockets=1, socket_contents='filled', socket_items=(filler,))
        rows = [
            ('low-rolls', 'positive', item, MIGHT),
            ('upgraded', 'positive', replace(item, base=upgrade), MIGHT),
            ('wrong-merc', 'negative', item, {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {**MIGHT, 'player_class': 'Sorceress'}),
            ('unknown-sockets', 'unknown', replace(item, sockets=None), MIGHT),
            ('wrong-filler', 'negative', replace(item, socket_items=(SocketItem('El Rune'),)), MIGHT),
            ('unread-filler', 'unknown', replace(item, socket_items=()), MIGHT),
            ('empty', 'negative', replace(item, socket_contents='empty', socket_items=()), MIGHT),
        ]
        if item.rarity == 'set':
            rows.append(('impossible-ethereal', 'negative', replace(item, ethereal=True), MIGHT))
        elif slug == 'gaze-scintillating':
            rows.extend(
                [
                    ('nonethereal', 'negative', replace(item, ethereal=False), MIGHT),
                    ('unknown-ethereal', 'unknown', replace(item, ethereal=None), MIGHT),
                    ('pure-ias', 'negative', replace(item, socket_items=(IAS,)), MIGHT),
                    (
                        'lower-resist-tier',
                        'negative',
                        replace(
                            item,
                            socket_items=(
                                SocketItem(
                                    'Jewel', ((93, 0, 15), *((s, 0, 10) for s in (39, 41, 43, 45))), complete=True
                                ),
                            ),
                        ),
                        MIGHT,
                    ),
                ]
            )
        else:
            rows.append(('ethereal', 'positive', replace(item, ethereal=True), MIGHT))
        if filler.base == 'Jewel':
            rows.append(('unread-jewel-stats', 'unknown', replace(item, socket_items=(SocketItem('Jewel'),)), MIGHT))
        for label, scenario, candidate, context in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/merc-named/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(candidate.name, 'Trade tier:') if scenario == 'positive' else (candidate.name,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        + f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
