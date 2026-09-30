"""Actual IAS/fire-resistance jewel, independent of Andariel's native rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'abyss-warlock-merc-andariel-ias-fire'
CONTEXT = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
JEWEL = SocketItem('Jewel', ((93, 0, 15), (39, 0, 30)), complete=True)
ITEM = Item(
    'Demonhead',
    'unique',
    "Andariel's Visage",
    ((93, 0, 35), (39, 0, 0), (45, 0, 70), (46, 0, 10), (60, 0, 8), (0, 0, 25), (127, 0, 2), (16, 0, 100)),
    ethereal=True,
    sockets=1,
    socket_contents='filled',
    socket_items=(JEWEL,),
)


def cases():
    examples = [
        ('native-low', ITEM, CONTEXT, 'positive'),
        ('wrong-merc', ITEM, {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
        ('unknown-merc', ITEM, {'player_class': 'Warlock'}, 'unknown'),
        ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, 'negative'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'unknown'),
        ('unread-filler', replace(ITEM, socket_items=()), CONTEXT, 'unknown'),
        ('ral-only', replace(ITEM, socket_items=(SocketItem('Ral Rune'),)), CONTEXT, 'negative'),
        ('ias-only', replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15),), True),)), CONTEXT, 'negative'),
        (
            'fire-near-miss',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 29)), True),)),
            CONTEXT,
            'negative',
        ),
        ('partial-child', replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15),)),)), CONTEXT, 'unknown'),
    ]
    for label, item, context, scenario in examples:
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    side='merc',
                    rule_trace=IsPartialDict(
                        truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario],
                    ),
                )
            )
        }
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('93:0', '60:0', '0:0', '127:0', '39:0')
                    }
                )
            )
        yield Case(
            id='abyss/andariel/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario=scenario,
            absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
            report_contains=("Andariel's Visage", 'Trade tier:'),
            evidence=(
                'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/121',
            ),
        )


CASES = tuple(cases())
