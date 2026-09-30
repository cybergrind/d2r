"""Standalone Tal helm for Zeal; no Sorceress or set-completion bonuses assumed."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'zeal-paladin-tal-rashas-horadric-crest-named-alternative'
HELM = Item(
    'Death Mask',
    'set',
    "Tal Rasha's Horadric Crest",
    ((60, 0, 10), (62, 0, 10), (7, 0, 60 * 256), (9, 0, 30 * 256), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15)),
)
JEWELED = replace(
    HELM,
    sockets=1,
    socket_contents='filled',
    raw_stats=(*HELM.raw_stats, (93, 0, 15)),
    socket_items=(SocketItem('Jewel', ((93, 0, 15),), complete=True),),
)


def cases():
    result = []
    for scenario, label, item, context in (
        ('positive', 'native', HELM, {'player_class': 'Paladin'}),
        ('positive', 'upgraded', replace(HELM, base='Demonhead'), {'player_class': 'Paladin'}),
        ('positive', 'ias-jewel', JEWELED, {'player_class': 'Paladin'}),
        ('negative', 'other-class', HELM, {'player_class': 'Sorceress'}),
        ('unknown', 'unknown-class', HELM, {}),
        ('unknown', 'unknown-sockets', replace(HELM, sockets=None), {'player_class': 'Paladin'}),
    ):
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    rule_trace=IsPartialDict(
                        truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                    ),
                )
            )
        }
        if scenario == 'positive':
            keys = ('60:0', '62:0', '7:0', '9:0', '39:0', '41:0', '43:0', '45:0')
            if label == 'ias-jewel':
                keys += ('93:0',)
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in keys}
                )
            )
        result.append(
            Case(
                id=f'zeal/tal-helm/{label}',
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                report_contains=("Tal Rasha's Horadric Crest", 'Trade tier:'),
                absent_stat_configurations={'83:1': (ROLE + '-stats',), '127:0': (ROLE + '-stats',)},
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/105',
                    "third-parties/d2data/json/setitems.json:Tal Rasha's Horadric Crest",
                ),
            )
        )
    return tuple(result)


CASES = cases()
