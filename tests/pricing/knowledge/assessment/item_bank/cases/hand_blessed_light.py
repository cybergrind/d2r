"""FoH casting and its ethereal single-jewel Holy Bolt support preparation."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


PREFIX = 'fist-of-the-heavens-paladin-hand-of-blessed-light-'
MAIN = PREFIX + 'main-alternatives-delivery-weapon'
SUPPORT = PREFIX + 'holy-bolt-support-delivery-weapon'
CORE = {'83:3': 'desirable', '107:101': 'desirable', '107:121': 'desirable', '27:0': 'supporting', '31:0': 'supporting'}
JEWEL = ((99, 0, 7), (39, 0, 40), (41, 0, 10), (43, 0, 10), (45, 0, 10), (114, 0, 12))
EXTRA = {f'{s}:{p}': 'supporting' if s == 114 else 'desirable' for s, p, _ in JEWEL}
RAW = (
    (83, 3, 2),
    (107, 101, 4),
    (107, 121, 2),
    (27, 0, 15),
    (31, 0, 50),
    (17, 0, 130),
    (18, 0, 130),
    (119, 0, 100),
    (198, 7748, 5),
)


def cases():
    ctx = {'player_class': 'Paladin'}
    for base in ('Divine Scepter', 'Caduceus'):
        plain = Item(base, 'unique', 'Hand of Blessed Light', RAW, named_table_id=146)
        supported = replace(
            plain,
            ethereal=True,
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Jewel', JEWEL, True, rare=True),),
            raw_stats=(*RAW, *JEWEL, (194, 0, 1)),
        )
        rows = [
            ('ordinary-casting', plain, ctx, 'true', 'false', False),
            ('ethereal-casting', replace(plain, ethereal=True), ctx, 'true', 'true', False),
            ('unknown-ethereal', replace(plain, ethereal=None), ctx, 'true', 'unknown', False),
            ('support-jewel', supported, ctx, 'true', 'true', True),
            (
                'split-across-two-jewels',
                replace(
                    supported,
                    sockets=2,
                    raw_stats=(*RAW, *JEWEL, (194, 0, 2)),
                    socket_items=(
                        SocketItem('Jewel', JEWEL[:3], True, rare=True),
                        SocketItem('Jewel', JEWEL[3:], True, rare=True),
                    ),
                ),
                ctx,
                'false',
                'false',
                False,
            ),
            ('support-nonethereal', replace(supported, ethereal=False), ctx, 'true', 'false', False),
            ('wrong-class', supported, {'player_class': 'Sorceress'}, 'false', 'false', False),
            ('unknown-class', supported, {}, 'unknown', 'unknown', False),
            ('unidentified', replace(supported, identified=False), ctx, 'false', 'false', False),
            ('unread-parent', replace(supported, raw_stats=((194, 0, 1),)), ctx, 'true', 'true', True),
            (
                'unread-child',
                replace(supported, socket_items=(SocketItem('Jewel', rare=True),)),
                ctx,
                'true',
                'true',
                False,
            ),
            ('totals-only', replace(supported, socket_items=(), socket_contents='unknown'), ctx, 'true', 'true', False),
            (
                'empty-socket',
                replace(supported, socket_items=(), socket_contents='empty', raw_stats=(*RAW, (194, 0, 1))),
                ctx,
                'true',
                'true',
                False,
            ),
            (
                'unknown-sockets',
                replace(plain, ethereal=True, sockets=None, socket_contents='unknown'),
                ctx,
                'unknown',
                'unknown',
                False,
            ),
        ]
        for stat, layer, value in JEWEL:
            child = SocketItem(
                'Jewel',
                tuple((s, p, value - 1 if (s, p) == (stat, layer) else v) for s, p, v in JEWEL),
                True,
                rare=True,
            )
            rows.append((f'child-below-{stat}', replace(supported, socket_items=(child,)), ctx, 'true', 'true', False))
        for key in CORE:
            stat, layer = map(int, key.split(':'))
            rows.append(
                (
                    'unread-' + key,
                    replace(supported, raw_stats=tuple(s for s in supported.raw_stats if s[:2] != (stat, layer))),
                    ctx,
                    'true',
                    'true',
                    True,
                )
            )
        for label, item, context, main_truth, support_truth, support_active in rows:
            captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
            active_roles = [role for role, on in ((MAIN, main_truth == 'true'), (SUPPORT, support_active)) if on]
            annotations = {}
            for key in captured & (CORE.keys() | EXTRA.keys()):
                contributions = [
                    IsPartialDict(configuration_id=role + '-stats', role_id=role, desirability=(CORE | EXTRA)[key])
                    for role in active_roles
                    if key in CORE or role == SUPPORT
                ]
                if contributions:
                    annotations[key] = IsPartialDict(contributions=Contains(*contributions))
            expected = {
                'roles': Contains(
                    IsPartialDict(id=MAIN, rule_trace=IsPartialDict(truth=main_truth)),
                    IsPartialDict(id=SUPPORT, rule_trace=IsPartialDict(truth=support_truth)),
                )
            }
            if annotations:
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
            yield Case(
                id=f'hand-blessed-light/{base}/{label}',
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(MAIN, SUPPORT),
                scenario='unknown'
                if 'unknown' in (main_truth, support_truth) or label.startswith(('unread', 'totals'))
                else 'positive'
                if support_active or label == 'ordinary-casting'
                else 'negative',
                absent_configurations=tuple(role + '-stats' for role in (MAIN, SUPPORT) if role not in active_roles),
                absent_stat_configurations=dict.fromkeys(
                    ('17:0', '18:0', '119:0', '198:7748', *(k for k in CORE | EXTRA if k not in captured)),
                    (MAIN + '-stats', SUPPORT + '-stats'),
                ),
                detail_contains=('not hard-point synergies', 'Ethereal is accepted for casting only')
                if main_truth == 'true'
                else (),
                report_contains=('Hand of Blessed Light',) if item.identified else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/146',
                    'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/slots/Weapon/0',
                    'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/4/player/Weapon/0',
                ),
            )


CASES = tuple(cases())
