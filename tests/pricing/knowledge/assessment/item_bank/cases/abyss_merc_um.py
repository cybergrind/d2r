"""Abyss survival alternatives, including Um and irrelevant class/block bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_um import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


MIGHT = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
SPANS = {'guardian-angel': 106, 'rockstopper': 120}


def cases():
    result = []
    for slug, span, base, upgrade, keys, irrelevant in EXAMPLES:
        if slug not in SPANS:
            continue
        span = SPANS[slug]
        role = 'abyss-warlock-merc-um-' + slug
        item = replace(base, sockets=1, socket_contents='filled', socket_items=(SocketItem('Um Rune'),))
        rows = [
            ('low-rolls', 'positive', item, MIGHT),
            ('ethereal', 'positive', replace(item, ethereal=True), MIGHT),
            ('unknown-ethereal', 'positive', replace(item, ethereal=None), MIGHT),
            ('wrong-merc', 'negative', item, {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Warlock'}),
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
                    id=f'abyss/merc-um/{slug}/{label}',
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
                        f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
