"""Dream's slot-specific Jah effects and equipped companion stay distinct."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def dream(head, quality='normal', perfect=True):
    resistance = (20 if perfect else 5) + (0 if head else 45)
    return Item(
        'Bone Visage' if head else 'Sacred Targe',
        quality,
        'Dream',
        (
            (151, 118, 15),
            (99, 0, 30 if perfect else 20),
            (217, 0, 5 << 8),
            (31, 0, 378 if perfect else 308),
            (16, 0, 30),
            (3, 0, 10),
            (80, 0, 25 if perfect else 12),
            (201, 81 * 64 + 15, 10),
            (76, 0, 5) if head else (7, 0, 50 << 8),
            (194, 0, 3),
            *((stat, 0, resistance) for stat in (39, 41, 43, 45)),
        ),
        runeword='Dream',
        sockets=3,
        socket_contents='filled',
        socket_items=tuple(SocketItem(name + ' Rune') for name in ('Io', 'Jah', 'Pul')),
    )


def cases():
    for head, slot in ((True, 'helmets'), (False, 'off-hand')):
        role = f'dream-paladin-dream-{slot}-aura-recipe'
        config = role + '-stats'
        other_slot = 'off_hand' if head else 'head'
        for quality in ('normal', 'superior', 'low_quality'):
            item = dream(head, quality)
            context = {
                'player_class': 'Paladin',
                'player_equipment': {other_slot: normalize(dream(not head).capture()).to_dict()},
            }
            examples = (
                ('perfect', item, context, 'true', 'true'),
                ('minimum', dream(head, quality, False), context, 'true', 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false', 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', 'true'),
                (
                    'wrong-socket-count',
                    replace(
                        item,
                        sockets=2,
                        raw_stats=tuple(
                            (stat, layer, 2 if stat == 194 else value) for stat, layer, value in item.raw_stats
                        ),
                        socket_items=item.socket_items[:2],
                    ),
                    context,
                    'false',
                    'true',
                ),
                ('unknown-class', item, {'player_equipment': context['player_equipment']}, 'unknown', 'true'),
                (
                    'inventory-names-only',
                    item,
                    {'player_class': 'Paladin', 'player_items': ['Dream', 'Dream']},
                    'true',
                    'unknown',
                ),
                (
                    'companion-absent',
                    item,
                    {'player_class': 'Paladin', 'player_equipment': {other_slot: None}},
                    'true',
                    'false',
                ),
                (
                    'companion-wrong-slot-type',
                    item,
                    {'player_class': 'Paladin', 'player_equipment': {other_slot: normalize(item.capture()).to_dict()}},
                    'true',
                    'false',
                ),
            )
            for label, candidate, loadout, truth, companion in examples:
                assessment = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(IsPartialDict(status=companion)),
                        )
                    )
                }
                if truth == 'true' and companion == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('151:118', '99:0', '217:0', '80:0', '76:0' if head else '7:0')
                            }
                        )
                    )
                yield Case(
                    id=f'dream-pair/{slot}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**assessment)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' and companion == 'true' else (config,),
                    absent_stat_configurations={'7:0' if head else '76:0': (config,), '201:5199': (config,)},
                    report_contains=('Dream', 'Holy Shock'),
                    evidence=(
                        'pricing/raw/mr/planners/zb01066h.json:/data',
                        'third-parties/d2data/json/runes.json:/Dream',
                        'third-parties/d2data/json/gems.json:/r31',
                    ),
                )


CASES = tuple(cases())
