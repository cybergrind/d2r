"""Herald utility preserves total blocking, upgrades, and actual socket payloads."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Both native shield bases contribute22 block; Herald adds30, Eld adds7.
MINIMUM = (
    (83, 3, 2),
    (188, 24, 2),
    (16, 0, 150),
    (102, 0, 30),
    (20, 0, 52),
    (0, 0, 20),
    (3, 0, 20),
    (119, 0, 20),
    *((sid, 0, 50) for sid in (39, 41, 43, 45)),
)


def cases():
    for build, slot, index in (('fist-of-the-heavens-paladin', 'Off-Hand-Swap', 0), ('smite-paladin', 'Off-Hand', 3)):
        role = build + '-herald-of-zakarum-caster-shield-alternative'
        config = role + '-stats'
        item = Item('Gilded Shield', 'unique', 'Herald of Zakarum', MINIMUM)
        context = {'player_class': 'Paladin'}
        eld = replace(
            item,
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Eld Rune'),),
            raw_stats=(*tuple((sid, layer, 59 if sid == 20 else value) for sid, layer, value in MINIMUM), (194, 0, 1)),
        )
        for label, candidate, loadout, truth in (
            ('minimum', item, context, 'true'),
            (
                'maximum-defense',
                replace(
                    item, raw_stats=tuple((sid, layer, 200 if sid == 16 else value) for sid, layer, value in MINIMUM)
                ),
                context,
                'true',
            ),
            ('upgraded', replace(item, base='Zakarum Shield'), context, 'true'),
            ('eld', eld, context, 'true'),
            ('upgraded-eld', replace(eld, base='Zakarum Shield'), context, 'true'),
            ('open-socket', replace(item, sockets=1, raw_stats=(*MINIMUM, (194, 0, 1))), context, 'true'),
            (
                'unknown-contents',
                replace(item, sockets=1, socket_contents='unknown', raw_stats=(*MINIMUM, (194, 0, 1))),
                context,
                'true',
            ),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('impossible-sockets', replace(item, sockets=2), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in (
                                '83:3',
                                '188:24',
                                '102:0',
                                '20:0',
                                '0:0',
                                '3:0',
                                '39:0',
                                '41:0',
                                '43:0',
                                '45:0',
                                '16:0',
                            )
                        }
                    )
                )
            blocking = 59 if 'eld' in label else 52
            yield Case(
                id=f'herald-alternative/{build}/{label}',
                item=candidate,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations={'119:0': (config,)},
                report_contains=(
                    'Herald of Zakarum',
                    'Trade tier:',
                    f'Shield blocking (base + bonuses): {blocking}%',
                    *(('Sockets: 1 — Eld',) if 'eld' in label else ()),
                    *(('(150-200%)',) if label in ('minimum', 'maximum-defense', 'upgraded') else ()),
                )
                if candidate.identified
                else (),
                report_absent=(f'{blocking}% Increased Chance of Blocking',),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/{slot}/{index}',
                    'third-parties/d2data/json/uniqueitems.json:/285',
                    'third-parties/d2data/json/armor.json:/pa9',
                    'third-parties/d2data/json/armor.json:/pae',
                    'third-parties/d2data/json/gems.json:/r02',
                ),
            )


CASES = tuple(cases())
