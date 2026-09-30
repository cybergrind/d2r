"""Abyss MF Shako is conditional on main-loadout FCR, not perfect defense or sockets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_helmets import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


ROLE = 'abyss-warlock-build-guide-2-harlequin'


def cases():
    item = replace(EXAMPLES[0][1], raw_stats=(*EXAMPLES[0][1].raw_stats, (31, 0, 98)))
    context = {'player_class': 'Warlock', 'player_total_fcr': 125}
    for label, candidate, loadout, truth in (
        ('minimum-defense', item, context, 'true'),
        ('socketed-empty', replace(item, sockets=1), context, 'true'),
        ('unknown-sockets', replace(item, sockets=None), context, 'true'),
        ('perfect-defense', replace(item, raw_stats=(*item.raw_stats[:-1], (31, 0, 141))), context, 'true'),
        ('ethereal', replace(item, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', item, {'player_total_fcr': 125}, 'unknown'),
        ('below-fcr', item, {**context, 'player_total_fcr': 124}, 'false'),
        ('unknown-fcr', item, {'player_class': 'Warlock'}, 'unknown'),
    ):
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in ('127:0', '80:0')}
                )
            )
        yield Case(
            id='abyss/mf-shako/' + label,
            item=candidate,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=('Harlequin Crest', 'Trade tier:') if truth == 'true' else ('Shako',),
            evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
        )


CASES = tuple(cases())
