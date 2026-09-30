"""Independent low-roll examples for the guide's Um-filled survival equipment."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


MIGHT = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}
RES = tuple((stat, 0, 15) for stat in (39, 41, 43, 45))
EXAMPLES = (
    (
        'guardian-angel',
        224,
        Item(
            'Templar Coat',
            'unique',
            'Guardian Angel',
            (
                (16, 0, 180),
                (40, 0, 15),
                (42, 0, 15),
                (44, 0, 15),
                (46, 0, 15),
                (83, 3, 1),
                (102, 0, 30),
                (20, 0, 20),
                *RES,
            ),
        ),
        'Hellforge Plate',
        ('40:0', '42:0', '44:0', '46:0'),
        ('83:3', '102:0', '20:0'),
    ),
    (
        'gladiators-bane',
        222,
        Item(
            'Wire Fleece',
            'unique',
            "The Gladiator's Bane",
            ((16, 0, 150), (34, 0, 15), (35, 0, 15), (153, 0, 1), (99, 0, 30), (110, 0, 50), *RES),
        ),
        None,
        ('34:0', '35:0', '153:0', '99:0', '110:0'),
        (),
    ),
    (
        'rockstopper',
        235,
        Item(
            'Sallet',
            'unique',
            'Rockstopper',
            ((16, 0, 160), (36, 0, 10), (99, 0, 30), (39, 0, 35), (41, 0, 35), (43, 0, 35), (45, 0, 15), (3, 0, 15)),
        ),
        'Hydraskull',
        ('36:0', '99:0'),
        ('3:0',),
    ),
)


def cases():
    result = []
    for slug, span, base, upgrade, keys, irrelevant in EXAMPLES:
        role = 'zeal-paladin-merc-um-' + slug
        item = replace(base, sockets=1, socket_contents='filled', socket_items=(SocketItem('Um Rune'),))
        rows = [
            ('low-rolls', 'positive', item, MIGHT),
            ('ethereal', 'positive', replace(item, ethereal=True), MIGHT),
            ('unknown-ethereal', 'positive', replace(item, ethereal=None), MIGHT),
            ('wrong-merc', 'negative', item, {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {**MIGHT, 'player_class': 'Sorceress'}),
            ('unknown-sockets', 'unknown', replace(item, sockets=None), MIGHT),
            ('wrong-filler', 'negative', replace(item, socket_items=(SocketItem('El Rune'),)), MIGHT),
            ('unread-filler', 'unknown', replace(item, socket_items=()), MIGHT),
            ('empty', 'negative', replace(item, socket_contents='empty', socket_items=()), MIGHT),
            ('unsocketed', 'negative', replace(item, sockets=0, socket_contents='empty', socket_items=()), MIGHT),
        ]
        if upgrade:
            rows.append(('upgraded', 'positive', replace(item, base=upgrade), MIGHT))
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
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in (*keys, '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            result.append(
                Case(
                    id=f'zeal/merc-um/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(candidate.name,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
