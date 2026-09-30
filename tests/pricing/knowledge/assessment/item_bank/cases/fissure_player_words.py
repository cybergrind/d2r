"""Native Fissure player helmets: preferred staffmod versus optional ideal base."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    specs = (
        ('Lore', 'Antlers', 'starter-lore', ('Ort', 'Sol'), ((127, 0, 1), (107, 234, 1)), '107:234', 0),
        (
            'Flickering Flame',
            'Antlers',
            'standard-flickering-flame',
            ('Nef', 'Pul', 'Vex'),
            ((126, 1, 3), (333, 0, 10), (151, 100, 4), (9, 0, 50 * 256)),
            '333:0',
            1,
        ),
        (
            'Flickering Flame',
            'Bone Visage',
            'standard-flickering-flame',
            ('Nef', 'Pul', 'Vex'),
            ((126, 1, 3), (333, 0, 10), (151, 100, 4), (9, 0, 50 * 256)),
            '333:0',
            1,
        ),
    )
    for word, base, suffix, runes, stats, key, variant in specs:
        role = 'fissure-player-' + suffix
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                word,
                (*stats, (194, 0, len(runes))),
                sockets=len(runes),
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(n + ' Rune') for n in runes),
            )
            scenarios = [
                ('native', item, 'Druid', True),
                ('wrong-class', item, 'Paladin', False),
                ('unknown-class', item, None, False),
                ('ethereal', replace(item, ethereal=True), 'Druid', False),
                ('unknown-ethereal', replace(item, ethereal=None), 'Druid', False),
                ('unidentified', replace(item, identified=False), 'Druid', False),
                ('unmade', replace(item, runeword=None), 'Druid', False),
            ]
            if word == 'Lore':
                scenarios += [
                    (
                        'preferred-staffmod',
                        replace(item, raw_stats=((127, 0, 1), (107, 234, 3), (194, 0, 2))),
                        'Druid',
                        True,
                    ),
                    ('unknown-staffmod', replace(item, raw_stats=((127, 0, 1), (194, 0, 2))), 'Druid', False),
                ]
            for label, candidate, cls, usable in scenarios:
                yield Case(
                    id=f'fissure-player-word/{suffix}/{base}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': cls},
                    covers=(role,),
                    scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {key: IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                                )
                            )
                        )
                    }
                    if usable
                    else {},
                    absent_configurations=() if usable else (role + '-stats',),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/fissure-druid/variants/{variant}',
                        f'third-parties/d2data/json/runes.json:/{word}',
                    ),
                )


CASES = tuple(cases())
