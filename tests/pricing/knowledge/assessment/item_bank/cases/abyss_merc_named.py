"""Abyss Might mercenary alternatives, using independently authored native fixtures."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_named import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


SPANS = {
    'shaftstop-um': 104,
    'duriel-um': 105,
    'tal-amethyst': 114,
    'guillaume-ias': 115,
    'gaze-ias': 116,
    'stealskull-ias': 118,
    'kira-ral': 119,
}


def cases():
    result = []
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    for slug, _, native, filler, keys, irrelevant, upgrade in EXAMPLES:
        if slug not in SPANS:
            continue
        role = 'abyss-warlock-merc-' + slug
        item = replace(native, sockets=1, socket_contents='filled', socket_items=(filler,))
        scenarios = [
            ('native-low', item, context, 'positive'),
            ('upgraded', replace(item, base=upgrade), context, 'positive'),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', item, {'player_class': 'Warlock'}, 'unknown'),
            ('wrong-filler', replace(item, socket_items=(SocketItem('El Rune'),)), context, 'negative'),
            ('unread-filler', replace(item, socket_items=()), context, 'unknown'),
        ]
        if item.rarity == 'set':
            scenarios.append(('impossible-ethereal', replace(item, ethereal=True), context, 'negative'))
        else:
            scenarios.append(('ethereal', replace(item, ethereal=True), context, 'positive'))
        for label, candidate, ctx, scenario in scenarios:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
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
                    id=f'abyss/merc-named/{slug}/{label}',
                    item=candidate,
                    context=ctx,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(candidate.name, 'Trade tier:') if scenario == 'positive' else (candidate.name,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        + f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{SPANS[slug]}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
