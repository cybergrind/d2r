"""Independent native examples for the remaining completed-word quality families."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Word, role, base, class, mercenary (if any), ethereal, stats, benefit, runes.
SPECS = (
    (
        'Fortitude',
        'abyss-warlock-build-guide-1-merc-fortitude',
        'Sacred Armor',
        'Warlock',
        'Act 2 Might',
        True,
        ((39, 0, 25),),
        '39:0',
        ('El', 'Sol', 'Dol', 'Lo'),
    ),
    (
        'Chains of Honor',
        'echoing-strike-warlock-guide-1-merc-chains-honor',
        'Archon Plate',
        'Warlock',
        'Act 2 Prayer',
        True,
        ((60, 0, 8),),
        '60:0',
        ('Dol', 'Um', 'Ber', 'Ist'),
    ),
    (
        'Bulwark',
        'abyss-warlock-build-guide-0-merc-bulwark-native',
        'Bone Visage',
        'Warlock',
        'Act 2 Might',
        True,
        ((60, 0, 4),),
        '60:0',
        ('Shael', 'Io', 'Sol'),
    ),
    (
        'Treachery',
        'abyss-warlock-build-guide-0-merc-treachery-native',
        'Mage Plate',
        'Warlock',
        'Act 2 Might',
        True,
        ((93, 0, 45),),
        '93:0',
        ('Shael', 'Thul', 'Lem'),
    ),
    (
        'Call to Arms',
        'blizzard-mf-cta-prebuff',
        'Crystal Sword',
        'Sorceress',
        None,
        False,
        ((97, 149, 1), (97, 155, 2), (127, 0, 1)),
        '97:155',
        ('Amn', 'Ral', 'Mal', 'Ist', 'Ohm'),
    ),
    (
        'Spirit',
        'blizzard-starter-spirit-sword',
        'Crystal Sword',
        'Sorceress',
        None,
        False,
        ((105, 0, 25),),
        '105:0',
        ('Tal', 'Thul', 'Ort', 'Amn'),
    ),
    (
        'Rhyme',
        'berserk-barbarian-0-rhyme',
        'Bone Shield',
        'Barbarian',
        None,
        False,
        ((153, 0, 1),),
        '153:0',
        ('Shael', 'Eth'),
    ),
    (
        'Hustle (weapon)',
        'berserk-barbarian-merc-early-hustle-weapon-alternative',
        'Partizan',
        'Barbarian',
        'Act 2 Might',
        True,
        ((151, 122, 1),),
        '151:122',
        ('Shael', 'Ko', 'Eld'),
    ),
    (
        'Heart of the Oak',
        'double-throw-barbarian-guide-1-heart-oak',
        'Flail',
        'Barbarian',
        None,
        False,
        ((127, 0, 3),),
        '127:0',
        ('Ko', 'Vex', 'Pul', 'Thul'),
    ),
    (
        'Infinity',
        'nova-standard-infinity-player',
        'Scythe',
        'Sorceress',
        None,
        False,
        ((151, 123, 12), (334, 0, 45)),
        '334:0',
        ('Ber', 'Mal', 'Ber', 'Ist'),
    ),
    (
        'Flickering Flame',
        'fissure-player-standard-flickering-flame',
        'Antlers',
        'Druid',
        None,
        False,
        ((126, 1, 3), (333, 0, 10)),
        '333:0',
        ('Nef', 'Pul', 'Vex'),
    ),
    (
        'Lore',
        'fissure-player-starter-lore',
        'Antlers',
        'Druid',
        None,
        False,
        ((107, 234, 3), (127, 0, 1)),
        '127:0',
        ('Ort', 'Sol'),
    ),
)


def cases():
    for word, role, base, cls, merc, ethereal, stats, key, runes in SPECS:
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                word,
                (*stats, (194, 0, len(runes))),
                ethereal=ethereal,
                sockets=len(runes),
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(r + ' Rune') for r in runes),
            )
            context = {'player_class': cls, 'mercenary_type': merc}
            for label, candidate, usable in (
                ('native', item, True),
                ('unidentified', replace(item, identified=False), False),
                ('unknown-identification', replace(item, identified=None), False),
            ):
                yield Case(
                    id=f'remaining-word-quality/{word}/{quality}/{label}',
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
                    evidence=('third-parties/d2data/json/runes.json:/' + word, 'pricing/data/wp-a-builds.json'),
                )


CASES = tuple(cases())
