"""Zeal's Act 2 Might weapon, with separately verified socket setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Native uniqueitems326: lowest ED/leech; Decrepify is 33% at level1.
CORE = (
    (17, 0, 190),
    (18, 0, 190),
    (198, 87 * 64 + 1, 33),
    (60, 0, 11),
    (141, 0, 33),
    (115, 0, 1),
    (54, 0, 4),
    (55, 0, 44),
)
BASE = Item('Thresher', 'unique', "The Reaper's Toll", CORE)
RUBY = SocketItem('Jewel', ((17, 0, 31), (18, 0, 31), (93, 0, 15)), complete=True)
MIGHT = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}


def cases():
    result = []
    for slug, span in (('general', 206), ('shael', 209), ('ruby', 210)):
        role = 'zeal-paladin-reapers-' + slug
        item = BASE
        if slug == 'shael':
            item = replace(
                BASE,
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem('Shael Rune'),),
                raw_stats=(*CORE, (93, 0, 20)),
            )
        elif slug == 'ruby':
            item = replace(
                BASE,
                ethereal=True,
                sockets=1,
                socket_contents='filled',
                socket_items=(RUBY,),
                raw_stats=((17, 0, 221), (18, 0, 221), *CORE[2:], (93, 0, 15)),
                owned_stats=CORE,
            )
        rows = [
            ('low-rolls', 'positive', item, MIGHT),
            ('wrong-merc', 'negative', item, {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {**MIGHT, 'player_class': 'Sorceress'}),
            ('unknown-class', 'unknown', item, {'mercenary_type': 'Act 2 Might'}),
            ('different-unique', 'negative', Item('Giant Thresher', 'unique', 'Stormspire'), MIGHT),
            ('unknown-sockets', 'unknown', replace(item, sockets=None), MIGHT),
        ]
        if slug == 'general':
            rows.extend(
                [
                    ('ethereal', 'positive', replace(item, ethereal=True), MIGHT),
                    ('unknown-ethereal', 'positive', replace(item, ethereal=None), MIGHT),
                    ('impossible-sockets', 'negative', replace(item, sockets=2), MIGHT),
                ]
            )
        else:
            rows.extend(
                [
                    ('wrong-filler', 'negative', replace(item, socket_items=(SocketItem('El Rune'),)), MIGHT),
                    ('unread-children', 'unknown', replace(item, socket_items=()), MIGHT),
                    ('empty-socket', 'negative', replace(item, socket_contents='empty', socket_items=()), MIGHT),
                ]
            )
        if slug == 'ruby':
            rows.extend(
                [
                    ('nonethereal', 'negative', replace(item, ethereal=False), MIGHT),
                    ('unknown-ethereal', 'unknown', replace(item, ethereal=None), MIGHT),
                    (
                        'wrong-jewel-stats',
                        'negative',
                        replace(item, socket_items=(SocketItem('Jewel', ((39, 0, 30), (93, 0, 15)), complete=True),)),
                        MIGHT,
                    ),
                ]
            )
        for label, scenario, candidate, context in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={
                                'positive': 'true',
                                'negative': 'false',
                                'unknown': 'unknown',
                            }[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                keys = ('17:0', '198:5569', '60:0', '141:0') + (() if slug == 'general' else ('93:0',))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            if label == 'different-unique':
                expected['roles'] = ~Contains(IsPartialDict(id=role))
            result.append(
                Case(
                    id=f'zeal/reapers/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(candidate.name,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
