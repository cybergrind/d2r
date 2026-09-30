"""Starter mercenary armor, with bearer and quality boundaries kept independent."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    (
        'treachery',
        'Treachery',
        'Mage Plate',
        ((93, 0, 45), (201, 17103, 5), (99, 0, 20), (43, 0, 30)),
        ('Shael Rune', 'Thul Rune', 'Lem Rune'),
        ('93:0', '201:17103', '99:0', '43:0'),
    ),
    (
        'bulwark',
        'Bulwark',
        'Crown',
        ((60, 0, 4), (36, 0, 10), (76, 0, 5), (99, 0, 20)),
        ('Shael Rune', 'Io Rune', 'Sol Rune'),
        ('60:0', '36:0', '76:0', '99:0'),
    ),
)


def cases():
    for suffix, word, base, stats, runes, keys in USES:
        role = f'echoing-strike-warlock-guide-0-merc-{suffix}-native'
        context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Blessed Aim'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                word,
                (*stats, (194, 0, 3)),
                ethereal=True,
                sockets=3,
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(n) for n in runes),
            )
            rows = [
                ('positive', item, context, True),
                ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 2 Prayer'}, False),
                ('unknown-mercenary', item, {**context, 'mercenary_type': None}, False),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, False),
                ('unknown-ethereal', replace(item, ethereal=None), context, False),
                ('nonethereal', replace(item, ethereal=False), context, False),
                ('wrong-base', replace(item, base='Light Plate' if word == 'Treachery' else 'Cap'), context, False),
            ]
            for label, candidate, ctx, usable in rows:
                yield Case(
                    id=f'echoing/starter-{suffix}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                                )
                            )
                        )
                    }
                    if usable
                    else {},
                    absent_configurations=() if usable else (role + '-stats',),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/variants/0',
                        f'third-parties/d2data/json/runes.json:/{word}',
                    ),
                )


CASES = tuple(cases())
