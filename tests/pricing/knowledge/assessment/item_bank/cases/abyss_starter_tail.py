"""Starter Smoke and travel staff preserve wearer-specific utility and charge availability."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import emit
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    role = 'abyss-warlock-build-guide-starter-travel-staff'
    context = {'player_class': 'Warlock'}
    for quality in ('magic', 'rare'):
        item = Item('Long Staff', quality, raw_stats=((204, 3462, (33 << 8) | 1), (43, 0, 30)))
        for label, candidate, loadout, truth, scenario in (
            ('one-charge', item, context, 'true', 'positive'),
            ('ethereal-charge', replace(item, ethereal=True), context, 'true', 'positive'),
            ('depleted', replace(item, raw_stats=((204, 3462, 33 << 8), (43, 0, 30))), context, 'true', 'negative'),
            ('unread-charges', replace(item, raw_stats=((43, 0, 30),)), context, 'unknown', 'unknown'),
            ('wrong-class', item, {'player_class': 'Paladin'}, 'false', 'negative'),
            ('unknown-class', item, {}, 'unknown', 'unknown'),
        ):
            row = emit(role, label, candidate, loadout, truth, scenario, '204:3462')
            yield replace(row, id=f'abyss/starter-travel/{quality}/{label}')
    yield from smoke_cases()


def smoke_cases(build='abyss-warlock-build-guide', player_class='Warlock', prefix='abyss'):
    role = build + '-smoke-early-merc-resistance-alternative'
    original = next(item for slug, _, item, _ in EXAMPLES if slug == 'smoke')
    original = replace(original, raw_stats=(*original.raw_stats, (1, 0, 10), (204, 4614, (18 << 8) | 18)))
    context = {'player_class': player_class, 'mercenary_type': 'Act 2 Might'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = replace(original, rarity=quality)
        for label, candidate, loadout, truth in (
            ('native', item, context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ('empty', replace(item, socket_contents='empty'), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('wrong-count', replace(item, sockets=3), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress' if player_class != 'Sorceress' else 'Paladin'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('39:0', '41:0', '43:0', '45:0', '99:0', '32:0')
                        }
                    )
                )
            yield Case(
                id=f'{prefix}/starter-smoke/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(('1:0', '204:4614'), (role + '-stats',)),
                report_contains=('Smoke',),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
            )


CASES = tuple(cases())
