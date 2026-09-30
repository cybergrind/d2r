"""Tri-Brid Heaven's Light values skills, IAS and Crushing Blow, not weapon ED for Smite."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fist-of-the-heavens-paladin-heaven-s-light-tri-brid-delivery-weapon'
CONFIG = ROLE + '-stats'


def scepter(skills=2, ed=250):
    return Item(
        'Mighty Scepter',
        'unique',
        "Heaven's Light",
        ((83, 3, skills), (17, 0, ed), (18, 0, ed), (93, 0, 60), (136, 0, 33), (116, 0, 33), (194, 0, 2)),
        sockets=2,
        socket_contents='filled',
        socket_items=(SocketItem('Shael Rune'), SocketItem('Shael Rune')),
        named_table_id=371,
    )


def cases():
    context = {'player_class': 'Paladin'}
    original = scepter()
    rows = [
        (f'rolls-{skills}-{ed}', scepter(skills, ed), context, 'true', True) for skills in (2, 3) for ed in (250, 300)
    ]
    rows += [
        ('wrong-class', original, {'player_class': 'Sorceress'}, 'false', False),
        ('unknown-class', original, {}, 'unknown', False),
        ('ethereal', replace(original, ethereal=True), context, 'false', False),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown', False),
        ('unidentified', replace(original, identified=False), context, 'false', False),
        (
            'one-socket-shael',
            replace(
                original,
                sockets=1,
                socket_items=(SocketItem('Shael Rune'),),
                raw_stats=tuple((a, b, 40 if a == 93 else 1 if a == 194 else c) for a, b, c in original.raw_stats),
            ),
            context,
            'true',
            False,
        ),
        (
            'three-ias-jewels',
            replace(
                original,
                sockets=3,
                socket_items=tuple(SocketItem('Jewel', ((93, 0, 15),), True) for _ in range(3)),
                raw_stats=tuple((a, b, 65 if a == 93 else 3 if a == 194 else c) for a, b, c in original.raw_stats),
            ),
            context,
            'true',
            True,
        ),
        (
            'empty-native-ias',
            replace(
                original,
                socket_contents='empty',
                socket_items=(),
                raw_stats=tuple((a, b, 20 if a == 93 else c) for a, b, c in original.raw_stats),
            ),
            context,
            'true',
            False,
        ),
        (
            'unread-ias',
            replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != 93)),
            context,
            'true',
            False,
        ),
        (
            'observed-speed-unknown-fillers',
            replace(original, socket_contents='unknown', socket_items=()),
            context,
            'true',
            True,
        ),
    ]
    for label, item, loadout, truth, active in rows:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(
                            contributions=Contains(
                                IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability='desirable')
                            )
                        )
                        for key in ('83:3', '93:0', '136:0', '194:0')
                    }
                )
            )
        yield Case(
            id='foh-heavens-light/' + label,
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if label.startswith(('unknown', 'unread')) else 'negative',
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '116:0'), (CONFIG,)),
            report_contains=("Heaven's Light", 'Trade tier:', 'item range: 2-3', 'item range: 250-300')
            if active
            else (),
            report_absent=('Shael',) if label == 'observed-speed-unknown-fillers' else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/3/player/Weapon/0',
                'third-parties/d2data/json/uniqueitems.json:/371',
            ),
        )


CASES = tuple(cases())
