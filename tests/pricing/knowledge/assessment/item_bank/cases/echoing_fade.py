"""Temporary Fade armor is distinct from ongoing player or mercenary equipment."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ARMOR = Item(
    'Breast Plate',
    'normal',
    'Treachery',
    raw_stats=((201, 17103, 5), (93, 0, 45), (99, 0, 20), (43, 0, 30), (194, 0, 3)),
    runeword='Treachery',
    sockets=3,
    socket_contents='filled',
    socket_items=tuple(SocketItem(rune) for rune in ('Shael Rune', 'Thul Rune', 'Lem Rune')),
)


def cases():
    for side in ('player', 'merc'):
        role = 'echoing-ubers-' + side + '-fade-prebuff'
        context = {'player_class': 'Warlock', 'mercenary_type': 'Act 5 Frenzy'}
        scenarios = [
            ('ready-to-trigger', ARMOR, context, 'true', True),
            ('ethereal', replace(ARMOR, ethereal=True), context, 'true', True),
            ('wrong-class', ARMOR, {**context, 'player_class': 'Paladin'}, 'false', False),
            ('unknown-class', ARMOR, {**context, 'player_class': None}, 'unknown', False),
            ('other-base', replace(ARMOR, base='Mage Plate'), context, 'false', False),
            (
                'wrong-count',
                replace(
                    ARMOR,
                    sockets=2,
                    socket_items=ARMOR.socket_items[:2],
                    raw_stats=tuple((i, layer, 2 if i == 194 else value) for i, layer, value in ARMOR.raw_stats),
                ),
                context,
                'false',
                False,
            ),
            (
                'unknown-count',
                replace(
                    ARMOR,
                    sockets=None,
                    socket_items=(),
                    socket_contents='unknown',
                    raw_stats=tuple(stat for stat in ARMOR.raw_stats if stat[0] != 194),
                ),
                context,
                'unknown',
                False,
            ),
            ('empty-sockets', replace(ARMOR, socket_contents='empty', socket_items=()), context, 'false', False),
            ('unknown-contents', replace(ARMOR, socket_contents='unknown', socket_items=()), context, 'unknown', False),
            ('unidentified', replace(ARMOR, identified=False), context, 'false', False),
            (
                'unread-fade',
                replace(ARMOR, raw_stats=tuple(s for s in ARMOR.raw_stats if s[0] != 201)),
                context,
                'true',
                False,
            ),
        ]
        if side == 'merc':
            scenarios += [
                ('wrong-mercenary', ARMOR, {**context, 'mercenary_type': 'Act 2 Might'}, 'false', False),
                ('unknown-mercenary', ARMOR, {**context, 'mercenary_type': None}, 'unknown', False),
            ]
        for label, item, loadout, truth, annotation in scenarios:
            expected = {
                'roles': Contains(
                    IsPartialDict(id=role, side=side, slot='Prebuff', rule_trace=IsPartialDict(truth=truth))
                )
            }
            if annotation:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({'201:17103': IsPartialDict(configuration_ids=Contains(role + '-stats'))})
                )
            yield Case(
                id=f'echoing/fade/{side}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario='unknown'
                if 'unknown' in label or label == 'unread-fade'
                else 'positive'
                if annotation
                else 'negative',
                absent_configurations=() if annotation else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(('93:0', '99:0', '43:0'), (role + '-stats',)),
                evidence=(
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/24',
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/25',
                    'third-parties/d2data/json/runes.json:/Treachery',
                ),
            )


CASES = tuple(
    replace(case, id=case.id + '/' + quality, item=replace(case.item, rarity=quality))
    for case in cases()
    for quality in ('normal', 'superior', 'low_quality')
)
