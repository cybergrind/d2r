"""Native Phoenix caster alternatives: shield survival and weapon effects differ."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('fire-warlock-guide', 'Warlock', 'off-hand', 'Monarch'),
    ('fissure-druid', 'Druid', 'off-hand', 'Monarch'),
    ('fissure-druid', 'Druid', 'weapon', 'Crystal Sword'),
)
COMMON = ((17, 0, 350), (18, 0, 350), (32, 0, 350), (151, 124, 10), (143, 0, 15), (333, 0, 28), (194, 0, 4))
SHIELD = ((40, 0, 10), (42, 0, 5), (7, 0, 50 * 256))
WEAPON = ((62, 0, 14), (141, 0, 20), (115, 0, 1))
RUNES = ('Vex', 'Vex', 'Lo', 'Jah')


def cases():
    for build, player, slot, base in SPECS:
        shield = slot == 'off-hand'
        role = f'{build}-phoenix-{slot}-aura-recipe'
        config = role + '-stats'
        context = {'player_class': player}
        keys = ('333:0', '151:124', '143:0', '32:0', *(('40:0', '42:0', '7:0') if shield else ()))
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Phoenix',
                (*COMMON, *(SHIELD if shield else WEAPON)),
                sockets=4,
                socket_contents='filled',
                runeword='Phoenix',
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in RUNES),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple(
                (sid, layer, {17: 400, 18: 400, 32: 400, 151: 15, 143: 21}.get(sid, value))
                for sid, layer, value in native.raw_stats
            )
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false' if shield else 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown' if shield else 'true'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
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
                    id=f'phoenix-caster/{build}/{slot}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '62:0', '141:0', '115:0'), (config,)),
                    report_contains=(
                        'Phoenix',
                        *(
                            ('Sockets: 4 — Vex, Vex, Lo, Jah', '(10-15)', '(15-21)')
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/{"Off-Hand" if shield else "Weapon"}',
                        'third-parties/d2data/json/runes.json:/Phoenix',
                        *(f'third-parties/d2data/json/gems.json:/{code}' for code in ('r26', 'r28', 'r31')),
                    ),
                )
            for label, candidate in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items)))),
                ('wrong-slot', replace(native, base='Crystal Sword' if shield else 'Monarch')),
            ):
                yield Case(
                    id=f'phoenix-caster/{build}/{slot}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(config,),
                    evidence=('third-parties/d2data/json/runes.json:/Phoenix',),
                )


CASES = tuple(cases())
