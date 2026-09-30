"""Gull loot swaps: all upgrade bases, legal sockets and passive ethereal use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Warlock': (
        'abyss-warlock-build-guide',
        'echoing-strike-warlock-guide',
        'fire-warlock-guide',
        'mirrored-blades-warlock-guide',
    ),
    'Paladin': ('blessed-hammer-paladin', 'fist-of-the-heavens-paladin'),
    'Sorceress': ('blizzard-sorceress', 'meteor-sorceress'),
}


def cases():
    for player_class, guides in USES.items():
        roles = tuple(g + '-gull-weapon-swap-find-weapon-alternative' for g in guides)
        configs = tuple(r + '-stats' for r in roles)
        for base in ('Dagger', 'Poignard', 'Bone Knife'):
            item = Item(base, 'unique', 'Gull', raw_stats=((21, 0, 1), (22, 0, 15), (80, 0, 100), (9, 0, -5 << 8)))
            context = {'player_class': player_class}
            examples = (
                ('intact', item, context, 'true'),
                ('open-socket', replace(item, sockets=1), context, 'true'),
                ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
                ('ethereal-passive', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('illegal-sockets', replace(item, sockets=2), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict({'80:0': IsPartialDict(configuration_ids=Contains(*configs))})
                    )
                yield Case(
                    id=f'gull-swaps/{player_class}/{base}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=roles,
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations=dict.fromkeys(('21:0', '22:0', '9:0'), configs),
                    report_contains=('Gull', '100% Better Chance of Getting Magic Items', 'Trade tier:')
                    if truth == 'true'
                    else (base,),
                    evidence=(
                        'third-parties/d2data/json/uniqueitems.json:/39',
                        *(f'pricing/data/wp-a-builds.json:/{g}/slots/Weapon-Swap/2' for g in guides),
                    ),
                )


CASES = tuple(cases())
