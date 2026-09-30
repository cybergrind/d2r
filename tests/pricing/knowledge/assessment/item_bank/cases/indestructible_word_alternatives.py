"""Oath attack utility versus Death Smite utility, with observed durability gates."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


OATH_STATS = (
    (17, 0, 210),
    (18, 0, 210),
    (93, 0, 50),
    (147, 0, 10),
    (152, 0, 1),
    (121, 0, 75),
    (123, 0, 100),
    (117, 0, 1),
    (1, 0, 10),
    (194, 0, 4),
    (198, 93 * 64 + 20, 30),
    (204, 90 * 64 + 17, (14 << 8) | 14),
    (204, 236 * 64 + 16, (20 << 8) | 20),
)
DEATH_STATS = (
    (17, 0, 300),
    (18, 0, 300),
    (136, 0, 50),
    (250, 0, 4),
    (152, 0, 1),
    (91, 0, -20),
    (19, 0, 50),
    (89, 0, 1),
    (62, 0, 7),
    (119, 0, 20),
    (50, 0, 1),
    (51, 0, 50),
    (194, 0, 5),
    (195, 55 * 64 + 18, 25),
    (197, 53 * 64 + 44, 100),
    (204, 85 * 64 + 22, (15 << 8) | 15),
)


def cases():
    for name, base, player, role, stats, runes, locator in (
        (
            'Oath',
            'Balrog Blade',
            'Barbarian',
            'gold-find-barbarian-oath-balrog-blade-combat-word-alternative',
            OATH_STATS,
            ('Shael', 'Pul', 'Mal', 'Lum'),
            '/gold-find-barbarian/slots/Weapon/1',
        ),
        (
            'Death',
            'Berserker Axe',
            'Paladin',
            'smite-paladin-death-berserker-axe-combat-word-alternative',
            DEATH_STATS,
            ('Hel', 'El', 'Vex', 'Ort', 'Gul'),
            '/smite-paladin/slots/Weapon/2',
        ),
    ):
        config = role + '-stats'
        oath = name == 'Oath'
        context = {'player_class': player}
        keys = ('17:0', '18:0', '93:0', '147:0', '121:0', '123:0') if oath else ('136:0',)
        excluded = ('198:5972', '204:5777', '204:15120') if oath else ('17:0', '18:0', '250:0', '62:0', '19:0', '119:0')
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                name,
                stats,
                ethereal=True,
                sockets=len(runes),
                socket_contents='filled',
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in runes),
                runeword=name,
                complete=True,
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple(
                (sid, layer, ({17: 340, 18: 340, 147: 15} if oath else {17: 385, 18: 385}).get(sid, value))
                for sid, layer, value in stats
            )
            no_durability = tuple(s for s in stats if s[0] != 152)
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('non-ethereal', replace(native, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('missing-indestructible', replace(native, raw_stats=no_durability), context, 'false'),
                ('unread-indestructible', replace(native, raw_stats=no_durability, complete=False), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'indestructible-word/{name}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=(
                        name,
                        *(
                            (
                                f'Sockets: {len(runes)} — ' + ', '.join(runes),
                                ('(210-355%)' if quality == 'superior' else '(210-340%)')
                                if oath
                                else ('(300-400%)' if quality == 'superior' else '(300-385%)'),
                                'Indestructible',
                            )
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:{locator}',
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )
            for label, candidate in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('legal-word-wrong-guide-base', replace(native, base='Phase Blade', ethereal=False)),
            ):
                yield Case(
                    id=f'indestructible-word/{name}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=(f'pricing/data/wp-a-builds.json:{locator}',),
                )


CASES = tuple(cases())
