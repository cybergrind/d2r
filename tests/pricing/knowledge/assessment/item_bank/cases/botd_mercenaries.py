"""Gold Find and Enchant BotD alternatives retain different Act 2 aura setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


NAME = 'Breath of the Dying'
STATS = (
    (17, 0, 350),
    (18, 0, 350),
    (93, 0, 60),
    (60, 0, 12),
    (62, 0, 7),
    (0, 0, 30),
    (1, 0, 30),
    (2, 0, 30),
    (3, 0, 30),
    (122, 0, 200),
    (124, 0, 50),
    (19, 0, 50),
    (89, 0, 1),
    (91, 0, -20),
    (152, 0, 1),
    (116, 0, 25),
    (117, 0, 1),
    (196, 92 * 64 + 20, 50),
    (194, 0, 6),
)


def cases():
    for build, player, merc, index in (
        ('gold-find-barbarian', 'Barbarian', 'Act 2 Might', 0),
        ('enchant-sorceress', 'Sorceress', 'Act 2 Prayer', 1),
    ):
        role = build + '-breath-of-the-dying-end-merc-weapon-alternative'
        config = role + '-stats'
        context = {'player_class': player, 'mercenary_type': merc}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'War Pike',
                quality,
                NAME,
                STATS,
                ethereal=True,
                sockets=6,
                socket_contents='filled',
                runeword=NAME,
                complete=True,
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in ('Vex', 'Hel', 'El', 'Eld', 'Zod', 'Eth')),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple((sid, layer, {17: 400, 18: 400, 60: 15}.get(sid, value)) for sid, layer, value in STATS)
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('non-ethereal', replace(native, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('wrong-act', native, {**context, 'mercenary_type': 'Act 1 Cold'}, 'false'),
                (
                    'wrong-act2-aura',
                    native,
                    {**context, 'mercenary_type': 'Act 2 Prayer' if merc == 'Act 2 Might' else 'Act 2 Might'},
                    'false',
                ),
                ('unknown-mercenary', native, {'player_class': player}, 'unknown'),
                ('wrong-owner', native, {**context, 'player_class': 'Paladin'}, 'false'),
                ('unknown-owner', native, {'mercenary_type': merc}, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
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
                                for key in ('17:0', '18:0', '93:0', '60:0', '0:0', '2:0', '122:0')
                            }
                        )
                    )
                yield Case(
                    id=f'botd-mercenary/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(('62:0', '196:5908', '117:0'), (config,)),
                    report_contains=(
                        NAME,
                        *(
                            (
                                'Sockets: 6 — Vex, Hel, El, Eld, Zod, Eth',
                                '(350-415%)' if quality == 'superior' else '(350-400%)',
                                '(12-15%)',
                                'Indestructible',
                                '200% Damage to Undead',
                            )
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/end/{index}',
                        f'pricing/data/wp-a-variants/{build}.json:/variants/1/merc/type',
                        'third-parties/d2data/json/runes.json:/Breath of the Dying',
                        'third-parties/d2data/json/gems.json:/r02',
                    ),
                )
            for label, candidate in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('sword-not-act2-weapon', replace(native, base='Colossus Blade')),
            ):
                yield Case(
                    id=f'botd-mercenary/{build}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=('third-parties/d2data/json/runes.json:/Breath of the Dying',),
                )


CASES = tuple(cases())
