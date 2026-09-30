"""Fissure mercenary words retain bearer and companion requirements."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    specs = (
        (
            'standard-fortitude',
            'Fortitude',
            'Sacred Armor',
            ('El', 'Sol', 'Dol', 'Lo'),
            ((17, 0, 300), (18, 0, 300), (16, 0, 200)),
            '17:0',
            ('Infinity',),
            1,
        ),
        (
            'magic-find-fortitude',
            'Fortitude',
            'Sacred Armor',
            ('El', 'Sol', 'Dol', 'Lo'),
            ((17, 0, 300), (18, 0, 300), (16, 0, 200)),
            '17:0',
            ('Infinity',),
            2,
        ),
        (
            'ubers-chains-of-honor',
            'Chains of Honor',
            'Archon Plate',
            ('Dol', 'Um', 'Ber', 'Ist'),
            ((60, 0, 8), (39, 0, 65), (41, 0, 65), (43, 0, 65), (45, 0, 65)),
            '60:0',
            ('Infinity', 'Flickering Flame'),
            3,
        ),
        (
            'ubers-flickering-flame',
            'Flickering Flame',
            'Bone Visage',
            ('Nef', 'Pul', 'Vex'),
            ((151, 100, 4), (126, 1, 3), (333, 0, 10)),
            '151:100',
            ('Infinity', 'Chains of Honor'),
            3,
        ),
    )
    for suffix, word, base, runes, stats, key, companions, variant in specs:
        role = 'fissure-merc-' + suffix
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                word,
                (*stats, (194, 0, len(runes))),
                ethereal=True,
                sockets=len(runes),
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(n + ' Rune') for n in runes),
            )
            ctx = {'player_class': 'Druid', 'mercenary_type': 'Act 2 Might', 'mercenary_items': list(companions)}
            scenarios = [
                ('native', item, ctx, True),
                ('nonethereal', replace(item, ethereal=False), ctx, True),
                ('wrong-class', item, {**ctx, 'player_class': 'Paladin'}, False),
                ('unknown-class', item, {**ctx, 'player_class': None}, False),
                ('wrong-mercenary', item, {**ctx, 'mercenary_type': 'Act 1 Cold'}, False),
                ('unknown-mercenary', item, {**ctx, 'mercenary_type': None}, False),
                ('missing-companions', item, {**ctx, 'mercenary_items': []}, False),
                ('unidentified', replace(item, identified=False), ctx, False),
                ('holy-freeze', item, {**ctx, 'mercenary_type': 'Act 2 Holy Freeze'}, variant in (1, 2)),
            ]
            if word == 'Fortitude':
                scenarios += [
                    ('alternative-base', replace(item, base='Archon Plate'), ctx, True),
                    (
                        'nonethereal-holy-freeze',
                        replace(item, base='Archon Plate', ethereal=False),
                        {**ctx, 'mercenary_type': 'Act 2 Holy Freeze'},
                        True,
                    ),
                    ('unknown-companions', item, {**ctx, 'mercenary_items': None}, False),
                ]
            for label, candidate, context, usable in scenarios:
                yield Case(
                    id=f'fissure-merc-word/{suffix}/{quality}/{label}',
                    item=candidate,
                    context=context,
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
                    absent_stat_configurations=dict.fromkeys(('126:1', '333:0'), (role + '-stats',))
                    if word == 'Flickering Flame'
                    else {},
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/fissure-druid/variants/{variant}',
                        f'third-parties/d2data/json/runes.json:/{word}',
                    ),
                )


CASES = tuple(cases())
