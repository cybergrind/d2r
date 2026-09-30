"""Seven native mercenary recipes with independently chosen wearer and stat boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Word, base, build, suffix, class, native benefit, rune sequence.
SPECS = (
    (
        'Smoke',
        'Mage Plate',
        'echoing-strike-warlock-guide',
        'smoke-early-merc-resistance-alternative',
        'Warlock',
        (39, 0, 50),
        ('Nef', 'Lum'),
    ),
    (
        'Duress',
        'Mage Plate',
        'echoing-strike-warlock-guide',
        'duress-mid-merc-resistance-alternative',
        'Warlock',
        (136, 0, 15),
        ('Shael', 'Um', 'Thul'),
    ),
    (
        'Lionheart',
        'Mage Plate',
        'echoing-strike-warlock-guide',
        'early-merc-lionheart',
        'Warlock',
        (7, 0, 12800),
        ('Hel', 'Lum', 'Fal'),
    ),
    (
        'Temper',
        'Crown',
        'echoing-strike-warlock-guide',
        'early-merc-temper',
        'Warlock',
        (142, 0, 10),
        ('Shael', 'Io', 'Ral'),
    ),
    ('Ground', 'Crown', 'berserk-barbarian', 'ground-merc-early', 'Barbarian', (144, 0, 10), ('Shael', 'Io', 'Ort')),
    (
        'Hustle (armor)',
        'Mage Plate',
        'berserk-barbarian',
        'merc-early-hustle-armor-alternative',
        'Barbarian',
        (93, 0, 40),
        ('Shael', 'Ko', 'Eld'),
    ),
    (
        'Wealth',
        'Mage Plate',
        'gold-find-barbarian',
        'merc-wealth-body-armor-end-word-utility-alternative',
        'Barbarian',
        (80, 0, 100),
        ('Lem', 'Ko', 'Tir'),
    ),
)


def cases():
    for word, base, build, suffix, cls, stat, runes in SPECS:
        role = build + '-' + suffix
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                word,
                (stat, (194, 0, len(runes))),
                ethereal=False,
                sockets=len(runes),
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(r + ' Rune') for r in runes),
            )
            context = {'player_class': cls, 'mercenary_type': 'Act 2 Might'}
            for label, candidate, ctx, usable in (
                ('nonethereal', item, context, True),
                ('ethereal', replace(item, ethereal=True), context, True),
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, False),
                ('illegal-base', replace(item, base='Quilted Armor' if base == 'Crown' else 'Cap'), context, False),
                ('unknown-identified', replace(item, identified=None), context, False),
            ):
                yield Case(
                    id=f'merc-word-quality/{word}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {f'{stat[0]}:{stat[1]}': IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                                )
                            )
                        )
                    }
                    if usable
                    else {},
                    absent_configurations=() if usable else (role + '-stats',),
                    evidence=(f'pricing/raw/mr/guides__{build}.html', 'third-parties/d2data/json/runes.json:/' + word),
                )


CASES = tuple(cases())
