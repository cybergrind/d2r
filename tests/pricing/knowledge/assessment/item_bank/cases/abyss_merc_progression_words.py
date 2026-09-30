"""Early/mid mercenary words retain low-roll utility and reject player-only stat benefits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


REVIEWS = (
    ('lionheart', 'early-merc-lionheart', ('17:0', '7:0', '0:0', '2:0', '39:0'), 'Breast Plate', 'Quilted Armor'),
    ('temper', 'early-merc-temper', ('39:0', '142:0', '76:0', '99:0'), 'Mask', 'Cap'),
    (
        'duress',
        'duress-mid-merc-resistance-alternative',
        ('136:0', '135:0', '17:0', '99:0', '43:0'),
        'Dusk Shroud',
        'Quilted Armor',
    ),
)


def cases(build='abyss-warlock-build-guide', player_class='Warlock', prefix='abyss', reviews=REVIEWS):
    for slug, suffix, keys, alternate, too_small in reviews:
        original = next(item for label, _, item, _ in EXAMPLES if label == slug)
        if slug == 'lionheart':
            original = replace(original, raw_stats=(*original.raw_stats, (3, 0, 20)))
        role = build + '-' + suffix
        context = {'player_class': player_class, 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(original, rarity=quality)
            for label, candidate, loadout, truth in (
                ('native-low', item, context, 'true'),
                ('alternate-base', replace(item, base=alternate), context, 'true'),
                ('insufficient-base-capacity', replace(item, base=too_small), context, 'false'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('wrong-count', replace(item, sockets=2), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ):
                expected = {
                    'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'{prefix}/merc-progression-words/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(('1:0', '3:0'), (role + '-stats',)),
                    report_contains=(item.name,),
                    evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
