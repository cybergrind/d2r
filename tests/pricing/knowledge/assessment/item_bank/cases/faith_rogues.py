"""Faith aura support uses the specified Rogue; crossbow legality differs from recipe legality."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', 'Act 1 Fire', 'Great Bow'),
    ('dream-paladin', 'Paladin', 'Act 1 Cold', 'Matriarchal Bow'),
    ('lightning-strike-amazon', 'Amazon', 'Act 1 Cold', 'Matriarchal Bow'),
)
STATS = (
    (151, 122, 12),
    (127, 0, 1),
    (17, 0, 330),
    (18, 0, 330),
    (194, 0, 4),
    (39, 0, 15),
    (41, 0, 15),
    (43, 0, 15),
    (45, 0, 15),
)
RUNES = ('Ohm', 'Jah', 'Lem', 'Eld')


def cases():
    for build, player, merc, base in SPECS:
        source_index = 2 if build == 'dream-paladin' else 0
        role = f'{build}-faith-end-merc-weapon-alternative'
        config = role + '-stats'
        context = {'player_class': player, 'mercenary_type': merc}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Faith',
                STATS,
                sockets=4,
                socket_contents='filled',
                runeword='Faith',
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in RUNES),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple((sid, layer, {151: 15, 127: 2}.get(sid, raw)) for sid, layer, raw in STATS)
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('wrong-merc', native, {**context, 'mercenary_type': 'Act 2 Might'}, 'false'),
                (
                    'wrong-rogue',
                    native,
                    {**context, 'mercenary_type': 'Act 1 Cold' if merc == 'Act 1 Fire' else 'Act 1 Fire'},
                    'false',
                ),
                ('unknown-merc', native, {'player_class': player}, 'unknown'),
                ('wrong-player', native, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-player', native, {'mercenary_type': merc}, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('151:122', '127:0', '17:0', '39:0', '41:0', '43:0', '45:0')
                            }
                        )
                    )
                yield Case(
                    id=f'faith-rogue/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    report_contains=(
                        'Faith',
                        *(('Sockets: 4 — Ohm, Jah, Lem, Eld', '(12-15)', '(1-2)') if truth == 'true' else ()),
                    ),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/end/{source_index}',
                        f'pricing/data/wp-a-variants/{build}.json:/variants/1/merc/type',
                        'third-parties/d2data/json/runes.json:/Faith',
                    ),
                )
            for label, candidate in (
                ('crossbow', replace(native, base='Demon Crossbow')),
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
            ):
                yield Case(
                    id=f'faith-rogue/{build}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=('third-parties/d2data/json/runes.json:/Faith',),
                )


CASES = tuple(cases())
