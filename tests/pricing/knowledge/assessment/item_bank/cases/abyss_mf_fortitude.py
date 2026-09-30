"""Abyss MF mercenary armor: exact base/context, native minimum resistance, no FCR priority."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


ROLE = 'abyss-warlock-build-guide-2-merc-fortitude'


def cases():
    original = next(item for slug, _, item, _ in EXAMPLES if slug == 'fortitude')
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = replace(original, rarity=quality)
        for label, candidate, loadout, truth in (
            ('minimum-resists', item, context, 'true'),
            (
                'perfect-resists',
                replace(
                    item,
                    raw_stats=tuple(
                        (stat, layer, 30 if stat in (39, 41, 43, 45) else value)
                        for stat, layer, value in item.raw_stats
                    ),
                ),
                context,
                'true',
            ),
            ('nonethereal', replace(item, ethereal=False), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('empty', replace(item, socket_contents='empty'), context, 'false'),
            ('wrong-count', replace(item, sockets=3), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('different-armor', replace(item, base='Archon Plate'), context, 'false'),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
            ('unknown-merc', item, {'player_class': 'Warlock'}, 'unknown'),
            ('wrong-player-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
            ('unknown-player-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=ROLE, side='merc', rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                            for key in ('17:0', '16:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'abyss/mf-fortitude/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
                absent_stat_configurations={'105:0': (ROLE + '-stats',)},
                report_contains=('Fortitude',),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
            )


CASES = tuple(cases())
