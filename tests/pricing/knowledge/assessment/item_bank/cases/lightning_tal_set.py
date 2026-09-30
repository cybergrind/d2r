"""Three-piece Tal MF contribution needs companion pieces, FCR and the armor Ist."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


TAL = ("Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication")
ITEMS = (
    (
        'armor',
        Item(
            'Lacquered Plate',
            'set',
            TAL[0],
            ((80, 0, 113), (35, 0, 15), (39, 0, 40), (41, 0, 40), (43, 0, 40), (91, 0, -60), (31, 0, 941), (194, 0, 1)),
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Ist Rune'),),
            complete=True,
        ),
    ),
    *(
        (
            'belt',
            Item(
                base,
                'set',
                TAL[1],
                ((80, 0, 10), (9, 0, 30 << 8), (2, 0, 20), (114, 0, 37), (91, 0, -20)),
                complete=True,
            ),
        )
        for base in ('Mesh Belt', 'Mithril Coil')
    ),
    (
        'amulet',
        Item(
            'Amulet',
            'set',
            TAL[2],
            ((83, 1, 2), (7, 0, 50 << 8), (9, 0, 42 << 8), (41, 0, 33), (50, 0, 3), (51, 0, 32)),
            complete=True,
        ),
    ),
)


def cases():
    for piece, original in ITEMS:
        role = 'lightning-mf-tal-' + piece
        companions = [name for name in TAL if name != original.name]
        context = {'player_class': 'Sorceress', 'player_total_fcr': 117, 'player_items': companions}
        examples = [
            ('ready', original, context, 'true'),
            ('below-fcr', original, {**context, 'player_total_fcr': 116}, 'false'),
            ('unknown-fcr', original, {k: v for k, v in context.items() if k != 'player_total_fcr'}, 'unknown'),
            ('unknown-companions', original, {k: v for k, v in context.items() if k != 'player_items'}, 'unknown'),
            ('wrong-wearer', original, {**context, 'player_class': 'Warlock'}, 'false'),
            ('unknown-wearer', original, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            *(
                (f'missing-companion-{i}', original, {**context, 'player_items': [name]}, 'false')
                for i, name in enumerate(companions)
            ),
        ]
        for label, item, loadout, dependency in examples:
            yield Case(
                id=f'lightning-tal-set/{piece}/{item.base}/{label}',
                item=item,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[dependency],
                covers=(role,),
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                status='matched' if dependency == 'true' else 'partial',
                                rule_trace=IsPartialDict(truth='true'),
                                dependencies=Contains(IsPartialDict(status=dependency)),
                            )
                        )
                    )
                },
                report_contains=(item.name, 'Trade tier:'),
                evidence=('pricing/data/wp-a-variants/lightning-sorceress.json:/variants/2',),
            )


CASES = tuple(cases())
