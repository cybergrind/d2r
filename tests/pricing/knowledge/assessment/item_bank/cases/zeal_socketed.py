"""Actual socket children, not aggregate lookalikes, establish Zeal socket setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


GUILLAUME = Item(
    'Winged Helm',
    'set',
    "Guillaume's Face",
    ((136, 0, 35), (141, 0, 15), (99, 0, 30), (0, 0, 15)),
    sockets=1,
    socket_contents='filled',
)
GRISWOLD = Item(
    'Vortex Shield',
    'set',
    "Griswold's Honor",
    ((31, 0, 333), (102, 0, 65), (20, 0, 20), (39, 0, 45), (41, 0, 45), (43, 0, 45), (45, 0, 45), (80, 0, 75)),
    sockets=3,
    socket_contents='filled',
    socket_items=(SocketItem('Ist Rune'),) * 3,
)


def cases():
    rows = []
    for slug, span, child, raw in (
        ('cham', 88, SocketItem('Cham Rune'), ((153, 0, 1),)),
        ('um', 92, SocketItem('Um Rune'), ((39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15))),
        ('ber', 94, SocketItem('Ber Rune'), ((36, 0, 8),)),
        (
            'ruby',
            90,
            SocketItem('Jewel', ((17, 0, 31), (18, 0, 31), (93, 0, 15)), complete=True),
            ((17, 0, 31), (18, 0, 31), (93, 0, 15)),
        ),
    ):
        rows.append(
            (
                'zeal-paladin-socket-helm-' + slug,
                span,
                replace(GUILLAUME, raw_stats=(*GUILLAUME.raw_stats, *raw), socket_items=(child,)),
                tuple(f'{s}:{layer}' for s, layer, _ in (*GUILLAUME.raw_stats, *raw)),
            )
        )
    rows.append(
        (
            'zeal-paladin-griswold-s-honor-named-shield-tail',
            77,
            GRISWOLD,
            ('31:0', '102:0', '20:0', '39:0', '41:0', '43:0', '45:0', '80:0'),
        )
    )
    for quality in ('normal', 'superior'):
        for slug, span, raw, children in (
            ('topazes', 107, ((80, 0, 72),), (SocketItem('Perfect Topaz'),) * 3),
            (
                'resistance',
                109,
                ((39, 0, 30), (41, 0, 30), (43, 0, 30)),
                tuple(SocketItem(n) for n in ('Ral Rune', 'Ort Rune', 'Thul Rune')),
            ),
        ):
            item = Item('Mask', quality, raw_stats=raw, sockets=3, socket_contents='filled', socket_items=children)
            rows.append(('zeal-paladin-socket-helm-' + slug, span, item, tuple(f'{s}:{layer}' for s, layer, _ in raw)))
    result = []
    for role, span, item, keys in rows:
        wrong = replace(item, socket_items=(SocketItem('El Rune'),) * item.sockets)
        unknown = replace(item, socket_items=())
        for scenario, observed in (('positive', item), ('negative', wrong), ('unknown', unknown)):
            expected = {'roles': Contains(IsPartialDict(id=role))}
            if role.endswith(('-topazes', '-resistance', '-cham', '-um', '-ber')):
                status = {'positive': 'partial', 'negative': 'failed', 'unknown': 'partial'}[scenario]
                expected['roles'] = Contains(IsPartialDict(id=role, status=status))
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/socketed/{role}/{item.rarity}/{scenario}',
                    item=observed,
                    context={'player_class': 'Paladin'},
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(item.name or item.base,),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
