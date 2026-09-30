"""Completed fire helmets: native rolls, wearer and rune evidence stay separate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('enchant-sorceress', 'Sorceress'),
    ('fire-blast-assassin', 'Assassin'),
    ('fire-warlock-guide', 'Warlock'),
)
# Recipe plus Nef's missile defense, Pul's enhanced defense and Vex's maximum
# fire resistance. Half Freeze Duration is not Cannot Be Frozen.
STATS = (
    (126, 1, 3),
    (151, 100, 4),
    (333, 0, 10),
    (9, 0, 50 << 8),
    (118, 0, 1),
    (110, 0, 50),
    (32, 0, 30),
    (16, 0, 30),
    (40, 0, 5),
    (194, 0, 3),
)


def cases():
    for build, klass in SPECS:
        role = f'{build}-player-flickering flame-helmets-main-alternatives-helm-word-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Bone Visage',
                quality,
                'Flickering Flame',
                STATS,
                sockets=3,
                socket_contents='filled',
                runeword='Flickering Flame',
                complete=True,
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in ('Nef', 'Pul', 'Vex')),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple((sid, layer, {151: 8, 333: 15, 9: 75 << 8}.get(sid, raw)) for sid, layer, raw in STATS)
            examples = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
            )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('126:1', '151:100', '333:0', '9:0', '118:0', '110:0')
                            }
                        )
                    )
                yield Case(
                    id=f'flickering-caster/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    report_contains=(
                        'Flickering Flame',
                        'Nef, Pul, Vex',
                        '(4-8)',
                        '(10-15%)',
                        '(50-75)',
                        'Fire Skills',
                        'Half Freeze Duration',
                    )
                    if active
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Helmets/0',
                        'third-parties/d2data/json/runes.json:/Flickering Flame',
                        'third-parties/d2data/json/armor.json:/uh9',
                    ),
                )
            for label, candidate in (
                ('reversed-runes', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('wrong-base', replace(native, base='Mage Plate')),
            ):
                yield Case(
                    id=f'flickering-caster/{build}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    covers=(role,),
                    scenario='negative',
                    expected={},
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=('third-parties/d2data/json/runes.json:/Flickering Flame',),
                )


CASES = tuple(cases())
