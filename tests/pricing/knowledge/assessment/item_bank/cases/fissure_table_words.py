"""General helmet table alternatives do not require the Starter pelt's staffmod."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('Lore', 'Cap', 'fissure-druid-lore-progression-equipment', ('Ort', 'Sol'), ((127, 0, 1),), '127:0', 100),
    (
        'Flickering Flame',
        'Bone Visage',
        'fissure-druid-player-flickering flame-helmets-main-alternatives-helm-word-alternative',
        ('Nef', 'Pul', 'Vex'),
        ((126, 1, 3), (333, 0, 10), (151, 100, 4)),
        '333:0',
        92,
    ),
)


def cases():
    for word, base, role, runes, stats, key, span in SPECS:
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
            for label, candidate, cls, valid in (
                ('native', item, 'Druid', True),
                ('wrong-class', item, 'Barbarian', False),
                ('unknown-class', item, None, False),
                ('ethereal', replace(item, ethereal=True), 'Druid', False),
                ('unknown-ethereal', replace(item, ethereal=None), 'Druid', False),
                ('unmade', replace(item, runeword=None), 'Druid', False),
            ):
                yield Case(
                    id=f'fissure-table-word/{word}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': cls},
                    covers=(role,),
                    scenario='positive' if valid else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {key: IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                                )
                            )
                        )
                    }
                    if valid
                    else {},
                    absent_configurations=() if valid else (role + '-stats',),
                    evidence=(
                        f'pricing/raw/mr/guides__fissure-druid.html:/item-spans/{span}',
                        f'third-parties/d2data/json/runes.json:/{word}',
                    ),
                )


CASES = tuple(cases())
