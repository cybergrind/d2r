"""Chaos Prep uses Laying of Hands without assuming Disciple companions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'berserk-barbarian-4-laying-hands'
ITEM = Item('Bramble Mitts', 'set', 'Laying of Hands', ((93, 0, 20), (121, 0, 350), (39, 0, 50), (31, 0, 87)))


def cases():
    examples = [
        ('standalone', ITEM, {'player_class': 'Barbarian', 'player_items': []}, 'true'),
        ('unknown-companions', ITEM, {'player_class': 'Barbarian'}, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal-invalid', replace(ITEM, ethereal=True), {'player_class': 'Barbarian'}, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), {'player_class': 'Barbarian'}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), {'player_class': 'Barbarian'}, 'false'),
    ]
    for label, item, ctx, truth in examples:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('93:0', '121:0', '39:0')
                    }
                )
            )
        yield Case(
            id='chaos-gloves/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            absent_stat_configurations={'17:0': (ROLE + '-stats',), '18:0': (ROLE + '-stats',)},
            report_contains=('Laying of Hands',)
            if label in ('ethereal-invalid', 'unidentified')
            else ('Laying of Hands', 'Trade tier:'),
            report_absent=('Trade tier:',) if label in ('ethereal-invalid', 'unidentified') else (),
            evidence=(
                'pricing/raw/mr/planners/rb1d60lu.json:/data',
                'third-parties/d2data/json/setitems.json:/Laying of Hands',
            ),
        )


CASES = tuple(cases())
