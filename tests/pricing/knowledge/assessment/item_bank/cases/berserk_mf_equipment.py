"""Standard Berserk farming components, independent native low-roll examples.

wp-a-builds Standard explicitly separates 105 FCR weapon-swap mobility from
these main-loadout items. Guardian's Light is a separate socket contribution.
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_helmets import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    shako = replace(EXAMPLES[0][1], raw_stats=(*EXAMPLES[0][1].raw_stats, (31, 0, 98)))
    goldwrap = Item('Heavy Belt', 'unique', 'Goldwrap', ((80, 0, 30), (79, 0, 50), (93, 0, 10)))
    for slug, item, keys in (
        ('goldwrap', goldwrap, ('80:0', '79:0', '93:0')),
        ('harlequin', shako, ('127:0', '80:0')),
    ):
        role = 'berserk-barbarian-1-' + slug
        context = {'player_class': 'Barbarian'}
        rows = [
            ('minimum', item, context, 'true'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'true' if slug == 'goldwrap' else 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true' if slug == 'goldwrap' else 'unknown'),
            ('main-fcr-not-swap', item, {**context, 'player_total_fcr': 0}, 'true'),
        ]
        if slug == 'goldwrap':
            rows += [
                ('maximum-gold', replace(item, raw_stats=((80, 0, 30), (79, 0, 80), (93, 0, 10))), context, 'true'),
                ('exceptional', replace(item, base='Battle Belt'), context, 'true'),
                ('elite', replace(item, base='Troll Belt'), context, 'true'),
            ]
        else:
            rows += [
                ('maximum-defense', replace(item, raw_stats=(*item.raw_stats[:-1], (31, 0, 141))), context, 'true'),
                ('empty-socket', replace(item, sockets=1), context, 'true'),
                ('unknown-sockets', replace(item, sockets=None), context, 'true'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id='berserk/mf-equipment/' + slug + '/' + label,
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
