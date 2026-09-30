"""Tri-Brid Raven Frost supports CBF/blocking; AR does not improve its spells or Smite."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'fist-of-the-heavens-paladin-3-raven-frost'
FIXED = ((153, 0, 1), (148, 0, 20), (9, 0, 40 * 256), (54, 0, 15), (55, 0, 45), (56, 0, 100))
ITEM = Item('Ring', 'unique', 'Raven Frost', (*FIXED, (2, 0, 15), (19, 0, 150)))


def cases():
    context = {'player_class': 'Paladin'}
    examples = [
        ('minimum', ITEM, context, 'true'),
        ('perfect', replace(ITEM, raw_stats=(*FIXED, (2, 0, 20), (19, 0, 250))), context, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal-invalid', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ]
    for label, item, ctx, truth in examples:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('153:0', '148:0', '9:0', '2:0')
                    }
                )
            )
        yield Case(
            id='tribrid-raven/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            absent_stat_configurations={'19:0': (ROLE + '-stats',)},
            report_contains=('Raven Frost',),
            evidence=(
                'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/3',
                'third-parties/d2data/json/uniqueitems.json:/275',
            ),
        )


CASES = tuple(cases())
