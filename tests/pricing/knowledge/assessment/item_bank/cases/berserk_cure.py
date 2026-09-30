"""Early Cure is an intrinsic mercenary option, not proof of Prayer/Insight."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_early_merc import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


def cases(build='berserk-barbarian', player_class='Barbarian', prefix='berserk', source_index=6):
    role = build + '-early-merc-cure'
    original = next(item for slug, _, item, _ in EXAMPLES if slug == 'cure')
    original = replace(original, raw_stats=(*original.raw_stats, (3, 0, 10), (16, 0, 75)))
    context = {'player_class': player_class, 'mercenary_type': 'Act 2 Might', 'mercenary_items': []}
    for quality in ('normal', 'superior', 'low_quality'):
        item = replace(original, rarity=quality)
        rows = [
            ('minimum-no-insight', item, context, 'true'),
            ('maximum-poison-defense', replace(item, raw_stats=tuple(
                (s, layer, {45: 60, 16: 100}.get(s, v)) for s, layer, v in item.raw_stats
            )), context, 'true'),
            ('unknown-companions', item, {'player_class': player_class}, 'true'),
            ('prayer', item, {**context, 'mercenary_type': 'Act 2 Prayer'}, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ('normal-base', replace(item, base='Mask'), context, 'true'),
            ('circlet-base', replace(item, base='Diadem'), context, 'true'),
            ('insufficient-capacity', replace(item, base='Cap'), context, 'false'),
            ('empty', replace(item, socket_contents='empty'), context, 'false'),
            ('wrong-count', replace(item, sockets=2), context, 'false'),
            ('unknown-count', replace(item, sockets=None), context, 'unknown'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict({
                    key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                    for key in ('151:109', '45:0', '110:0', '76:0', '99:0')
                }))
            yield Case(
                id=f'{prefix}/cure/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations={'3:0': (role + '-stats',)},
                report_contains=('Cure',),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/merc/Helmet/early/{source_index}',
                          'third-parties/d2data/json/runes.json:/Cure'),
            )


CASES = tuple(cases())
