"""Pride's Concentration support across three sourced Act 2 Might alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', 1),
    ('mirrored-blades-warlock-guide', 'Warlock', 0),
    ('strafe-amazon', 'Amazon', 0),
)
STATS = (
    (151, 113, 16),
    (119, 0, 260),
    (50, 0, 50),
    (51, 0, 280),
    (243, 0, 8),
    (239, 0, 15),
    (74, 0, 8),
    (134, 0, 3),
    (113, 0, 1),
    (3, 0, 10),
    (141, 0, 20),
    (201, 51 * 64 + 17, 25),
    (194, 0, 4),
)


def cases():
    for build, player, index in SPECS:
        role = build + '-pride-end-merc-weapon-alternative'
        config = role + '-stats'
        context = {'player_class': player, 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Giant Thresher',
                quality,
                'Pride',
                STATS,
                ethereal=True,
                sockets=4,
                socket_contents='filled',
                runeword='Pride',
                complete=True,
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in ('Cham', 'Sur', 'Io', 'Lo')),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple((sid, layer, {151: 20, 119: 300}.get(sid, value)) for sid, layer, value in STATS)
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('non-ethereal', replace(native, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('wrong-mercenary-act', native, {**context, 'mercenary_type': 'Act 1 Cold'}, 'false'),
                ('wrong-mercenary-aura', native, {**context, 'mercenary_type': 'Act 2 Holy Freeze'}, 'false'),
                ('unknown-mercenary', native, {'player_class': player}, 'unknown'),
                ('wrong-player', native, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-player', native, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                assessment = {
                    'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))
                }
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('151:113', '119:0', '141:0', '74:0')
                            }
                        )
                    )
                yield Case(
                    id=f'pride-mercenary/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_annotations=('17:0', '18:0', '93:0', '60:0'),
                    absent_stat_configurations={'201:3281': (config,)},
                    report_contains=(
                        'Pride',
                        'Concentration',
                        *(
                            ('Sockets: 4 — Cham, Sur, Io, Lo', '(16-20)', '(260-300%)')
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/end/{index}',
                        'third-parties/d2data/json/runes.json:/Pride',
                        'third-parties/d2data/json/skills.json:/113',
                    ),
                )
            for label, candidate in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('incompatible-sword', replace(native, base='Phase Blade')),
            ):
                yield Case(
                    id=f'pride-mercenary/{build}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=('third-parties/d2data/json/runes.json:/Pride',),
                )


CASES = tuple(cases())
