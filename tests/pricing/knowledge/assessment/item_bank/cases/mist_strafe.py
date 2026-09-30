"""Source-specific Mist Matriarchal Bow: native bow skills remain separate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'strafe-amazon-mist-main-alternatives-source-recipe'
CONFIG = ROLE + '-stats'
STATS = (
    (17, 0, 325),
    (18, 0, 325),
    (127, 0, 3),
    (188, 0, 1),
    (151, 113, 8),
    (156, 0, 100),
    (93, 0, 20),
    (119, 0, 20),
    (3, 0, 24),
    (39, 0, 40),
    (41, 0, 40),
    (43, 0, 40),
    (45, 0, 40),
    (134, 0, 3),
    (54, 0, 3),
    (55, 0, 14),
    (56, 0, 75),
    (22, 0, 9),
    (194, 0, 5),
)


def cases():
    context = {'player_class': 'Amazon'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Matriarchal Bow',
            quality,
            'Mist',
            STATS,
            sockets=5,
            socket_contents='filled',
            runeword='Mist',
            complete=True,
            socket_items=tuple(SocketItem(rune + ' Rune') for rune in ('Cham', 'Shael', 'Gul', 'Thul', 'Ith')),
        )
        native = NativeRunewordItem(**vars(item))
        high = tuple((sid, layer, {17: 375, 18: 375, 151: 12, 188: 3}.get(sid, value)) for sid, layer, value in STATS)
        rows = (
            ('minimum-roll', native, context, 'true'),
            ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
            ('ethereal-bow', replace(native, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', native, {}, 'unknown'),
            ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
            ('wrong-amazon-bow', replace(native, base='Grand Matron Bow'), context, 'false'),
        )
        for label, candidate, loadout, truth in rows:
            assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(CONFIG))
                            for key in (
                                '17:0',
                                '18:0',
                                '127:0',
                                '188:0',
                                '151:113',
                                '156:0',
                                '93:0',
                                '119:0',
                                '3:0',
                                '39:0',
                                '41:0',
                                '43:0',
                                '45:0',
                            )
                        }
                    )
                )
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            if label in ('minimum-roll', 'maximum-roll'):
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(memory_stat=IsPartialDict(id=127), value=3),
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=188, layer=0),
                            value=1 if label == 'minimum-roll' else 3,
                        ),
                    )
                )
            yield Case(
                id=f'mist-strafe/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected=expected,
                covers=(ROLE,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (CONFIG,),
                report_contains=(
                    'Mist',
                    *(
                        (
                            'Sockets: 5 — Cham, Shael, Gul, Thul, Ith',
                            '(325-390%)' if quality == 'superior' else '(325-375%)',
                            '(8-12)',
                            'Bow and Crossbow Skills',
                            '(1-3)',
                            'All Skills',
                        )
                        if truth == 'true'
                        else ()
                    ),
                ),
                evidence=(
                    'pricing/data/wp-a-builds.json:/strafe-amazon/slots/Weapon/2',
                    'third-parties/d2data/json/runes.json:/Mist',
                    'third-parties/d2data/json/weapons.json:/amb',
                ),
            )
        yield Case(
            id=f'mist-strafe/{quality}/wrong-rune-order',
            item=replace(native, socket_items=tuple(reversed(native.socket_items))),
            context=context,
            expected={'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario='negative',
            absent_roles=(ROLE,),
            absent_configurations=(CONFIG,),
            evidence=('third-parties/d2data/json/runes.json:/Mist',),
        )


CASES = tuple(cases())
