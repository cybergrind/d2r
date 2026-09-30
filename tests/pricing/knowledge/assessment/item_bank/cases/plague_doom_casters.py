"""Plague and Doom have different spell/weapon contributions for each wearer."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


PLAGUE = (
    (17, 0, 220),
    (18, 0, 220),
    (127, 0, 1),
    (151, 109, 13),
    (336, 0, 23),
    (250, 0, 3),
    (93, 0, 20),
    (135, 0, 25),
    (134, 0, 3),
    (201, 91 * 64 + 12, 20),
    (198, 92 * 64 + 15, 25),
    (194, 0, 3),
)
DOOM = (
    (17, 0, 330),
    (18, 0, 330),
    (127, 0, 2),
    (151, 114, 12),
    (335, 0, 40),
    (93, 0, 45),
    (117, 0, 1),
    (135, 0, 25),
    (141, 0, 20),
    (134, 0, 3),
    (91, 0, -20),
    (198, 244 * 64 + 18, 5),
    (194, 0, 5),
)
SPECS = (
    ('Plague', 'echoing-strike-warlock-guide', 'Warlock', 1, ('Cryptic Sword', 'Fanged Knife')),
    ('Plague', 'poison-nova-necromancer', 'Necromancer', 1, ('Cryptic Sword', 'Fanged Knife')),
    ('Doom', 'echoing-strike-warlock-guide', 'Warlock', 8, ('Berserker Axe',)),
)


def cases():
    for name, build, player, index, bases in SPECS:
        plague = name == 'Plague'
        stats = PLAGUE if plague else DOOM
        runes = ('Cham', 'Shael', 'Um') if plague else ('Hel', 'Ohm', 'Um', 'Lo', 'Cham')
        role = f'{build}-player-{name.lower()}-weapon-main-alternatives-caster-word-remainder'
        config = role + '-stats'
        context = {'player_class': player}
        if plague:
            keys = ('127:0', '151:109', *(('17:0', '18:0', '250:0') if player == 'Warlock' else ('336:0',)))
            excluded = (
                '93:0',
                '135:0',
                '201:5836',
                '198:5903',
                *(('336:0',) if player == 'Warlock' else ('17:0', '18:0', '250:0')),
            )
        else:
            keys = ('127:0', '17:0', '18:0', '141:0', '151:114')
            excluded = ('93:0', '135:0', '335:0', '198:15634')
        for base in bases:
            for quality in ('normal', 'superior', 'low_quality'):
                item = Item(
                    base,
                    quality,
                    name,
                    stats,
                    sockets=len(runes),
                    socket_contents='filled',
                    socket_items=tuple(SocketItem(rune + ' Rune') for rune in runes),
                    runeword=name,
                    complete=True,
                )
                native = NativeRunewordItem(**vars(item))
                maxima = {17: 320, 18: 320, 127: 2, 151: 17} if plague else {17: 370, 18: 370, 335: 60}
                high = tuple((sid, layer, maxima.get(sid, value)) for sid, layer, value in stats)
                rows = (
                    ('minimum-roll', native, context, 'true'),
                    ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                    ('ethereal-casting', replace(native, ethereal=True), context, 'true'),
                    ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                    ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
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
                        id=f'plague-doom/{build}/{name}/{base}/{quality}/{label}',
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
                                    *(
                                        ('(220-335%)' if quality == 'superior' else '(220-320%)', '(1-2)', '(13-17)')
                                        if plague
                                        else ('(330-385%)' if quality == 'superior' else '(330-370%)', '(40-60%)')
                                    ),
                                )
                                if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                                else ()
                            ),
                        ),
                        evidence=(
                            f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon/{index}',
                            f'third-parties/d2data/json/runes.json:/{name}',
                            'third-parties/d2data/json/gems.json:/r27'
                            if not plague
                            else 'third-parties/d2data/json/gems.json:/r13',
                        ),
                    )
                for label, candidate in (
                    ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                    ('incompatible-base-or-class', replace(native, base='Runic Talons' if plague else 'Phase Blade')),
                ):
                    yield Case(
                        id=f'plague-doom/{build}/{name}/{base}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                        covers=(role,),
                        scenario='negative',
                        absent_roles=(role,),
                        absent_configurations=(config,),
                        evidence=(f'third-parties/d2data/json/runes.json:/{name}',),
                    )


CASES = tuple(cases())
