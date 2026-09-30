"""Explicit guide utility alternatives retain active-set limits and native upgrades."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_named_swaps import EXAMPLES, LIDLESS
from tests.pricing.knowledge.assessment.item_bank.models import Case


PREFIX = 'abyss-warlock-build-guide-'
REVIEWED = (
    (
        'gull',
        next(item for slug, _, item, _, _, _ in EXAMPLES if slug == 'gull'),
        'Bone Knife',
        ('gull-weapon-swap-find-weapon-alternative',),
        ('80:0',),
    ),
    (
        'ali-baba',
        next(item for slug, _, item, _, _, _ in EXAMPLES if slug == 'ali-baba'),
        'Hydra Edge',
        ('blade-of-ali-baba-weapon-swap-find-weapon-alternative',),
        ('240:0',),
    ),
    (
        'lidless',
        LIDLESS,
        'Troll Nest',
        ('lidless-wall-off-hand-shield-utility-alternative', 'lidless-wall-off-hand-swap-shield-utility-alternative'),
        ('127:0', '105:0', '77:0', '1:0', '138:0'),
    ),
)


def cases(build='abyss-warlock-build-guide', player_class='Warlock', prefix='abyss', reviewed=REVIEWED):
    for slug, item, upgrade, suffixes, keys in reviewed:
        roles = tuple(build + '-' + suffix for suffix in suffixes)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': player_class}
        rows = [
            ('native', item, context, 'true'),
            ('upgraded', replace(item, base=upgrade), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false' if slug == 'lidless' else 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown' if slug == 'lidless' else 'true'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('invalid-sockets', replace(item, sockets=3 if slug == 'ali-baba' else 2), context, 'false'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ]
        if slug != 'ali-baba':
            rows.append(('one-empty-socket', replace(item, sockets=1), context, 'true'))
        for label, candidate, loadout, truth in rows:
            expected = {
                'roles': Contains(
                    *[
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(truth=truth),
                            missing=Contains(FunctionCheck(lambda text: 'active' in text.casefold())),
                        )
                        for role in roles
                    ]
                )
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
            yield Case(
                id=f'{prefix}/loot-shield-alternatives/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '239:0'), configs),
                report_contains=(candidate.name, 'Trade tier:') if truth == 'true' else (candidate.name,),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
