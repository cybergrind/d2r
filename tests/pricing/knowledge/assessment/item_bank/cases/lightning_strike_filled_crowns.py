"""Magic Crown payloads are independent of the useful empty preparation base."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('topaz', ('Perfect Topaz',) * 3, ((80, 0, 72),), ('80:0',)),
    (
        'resist',
        ('Ral Rune', 'Ort Rune', 'Thul Rune'),
        ((39, 0, 30), (41, 0, 30), (43, 0, 30)),
        ('39:0', '41:0', '43:0'),
    ),
)


def cases():
    for slug, gems, raw, keys in SPECS:
        role = f'lightning-strike-amazon-{slug}-crown-filled'
        item = Item(
            'Crown',
            'magic',
            raw_stats=(*raw, (194, 0, 3)),
            sockets=3,
            socket_contents='filled',
            socket_items=tuple(SocketItem(name) for name in gems),
        )
        variants = [
            ('native', item, 'Amazon', True),
            ('reordered', replace(item, socket_items=item.socket_items[::-1]), 'Amazon', True),
            # Native Crown suffix "of the Wolf": 11-20 Life (magicsuffix entry 329).
            ('extra-modifier', replace(item, raw_stats=(*item.raw_stats, (7, 0, 20 * 256))), 'Amazon', True),
            ('normal-quality', replace(item, rarity='normal'), 'Amazon', False),
            ('rare-quality', replace(item, rarity='rare'), 'Amazon', False),
            ('empty', replace(item, socket_contents='empty', socket_items=()), 'Amazon', False),
            ('missing-child', replace(item, socket_items=item.socket_items[:2]), 'Amazon', False),
            ('wrong-children', replace(item, socket_items=(SocketItem('Perfect Ruby'),) * 3), 'Amazon', False),
            ('wrong-base', replace(item, base='Mask'), 'Amazon', False),
            ('ethereal', replace(item, ethereal=True), 'Amazon', False),
            ('unknown-ethereal', replace(item, ethereal=None), 'Amazon', False),
            ('unidentified', replace(item, identified=False), 'Amazon', False),
            ('wrong-class', item, 'Warlock', False),
            ('unknown-class', item, None, False),
        ]
        for stat, _, _ in raw:
            lowered = tuple((s, layer, value - 1 if s == stat else value) for s, layer, value in item.raw_stats)
            variants.append((f'low-effect-{stat}', replace(item, raw_stats=lowered), 'Amazon', False))
        for label, candidate, klass, active in variants:
            yield Case(
                id=f'lightning-strike-filled-crowns/{slug}/{label}',
                item=candidate,
                context={'player_class': klass},
                covers=(f'role:{role}:magic',),
                scenario='positive' if active else 'unknown' if label.startswith('unknown') else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=f'lightning-strike-amazon-{"resist" if slug == "topaz" else "topaz"}-crown-filled',
                                status='failed',
                            )
                        ),
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                            )
                        ),
                    )
                }
                if active
                else {},
                absent_configurations=() if active else (role + '-stats',),
                report_contains=('Sockets: 3', 'Perfect Topaz' if slug == 'topaz' else 'Ral, Ort, Thul')
                if active and label != 'reordered'
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/lightning-strike-amazon/slots/Helmets',
                    'third-parties/d2data/json/gems.json:helmet effects',
                ),
            )


CASES = tuple(cases())
