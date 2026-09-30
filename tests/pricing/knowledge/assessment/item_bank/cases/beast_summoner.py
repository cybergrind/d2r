"""Beast is a summon aura source; its wielder's melee modifiers do not transfer."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'summoner-necromancer-guide-player-beast-weapon-main-alternatives-caster-word-remainder'
CONFIG = ROLE + '-stats'
EVIDENCE = (
    'pricing/data/wp-a-builds.json:/summoner-necromancer-guide/slots/Weapon/1',
    'third-parties/d2data/json/runes.json:/Beast',
    'third-parties/d2data/json/gems.json:/r30',
    'third-parties/d2data/json/skills.json:/122',
)
STATS = (
    (151, 122, 9),
    (93, 0, 40),
    (17, 0, 240),
    (18, 0, 240),
    (0, 0, 25),
    (1, 0, 10),
    (138, 0, 2),
    (136, 0, 20),
    (135, 0, 25),
    (117, 0, 1),
    (97, 228, 3),
    (97, 224, 3),
    (204, 247 * 64 + 13, (5 << 8) | 5),
    (194, 0, 5),
)


def cases():
    context = {'player_class': 'Necromancer'}
    for base in ('Double Axe', 'War Scepter'):
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Beast',
                STATS,
                sockets=5,
                socket_contents='filled',
                runeword='Beast',
                socket_items=tuple(SocketItem(name + ' Rune') for name in ('Ber', 'Tir', 'Um', 'Mal', 'Lum')),
                complete=True,
            )
            native = NativeRunewordItem(**vars(item))
            maximum = tuple((sid, layer, {17: 270, 18: 270, 0: 40}.get(sid, value)) for sid, layer, value in STATS)
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=maximum), context, 'true'),
                ('ethereal-aura-only', replace(native, ethereal=True), context, 'true'),
                ('unknown-ethereal-aura-only', replace(item, ethereal=None), context, 'true'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(CONFIG))
                                for key in ('151:122', '0:0', '1:0', '138:0')
                            }
                        )
                    )
                yield Case(
                    id=f'beast-summoner/{base}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(ROLE,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (CONFIG,),
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0', '136:0', '135:0'), (CONFIG,)),
                    report_contains=(
                        'Beast',
                        *(
                            (
                                'Sockets: 5 — Ber, Tir, Um, Mal, Lum',
                                '(240-285%)' if quality == 'superior' else '(240-270%)',
                                '(25-40)',
                            )
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    evidence=EVIDENCE,
                )
            for label, candidate in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('sword-is-incompatible', replace(native, base='Crystal Sword')),
            ):
                yield Case(
                    id=f'beast-summoner/{base}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(ROLE,),
                    scenario='negative',
                    absent_roles=(ROLE,),
                    absent_configurations=(CONFIG,),
                    evidence=EVIDENCE,
                )


CASES = tuple(cases())
