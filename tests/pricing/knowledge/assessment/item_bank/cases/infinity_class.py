"""A build-specific Infinity benefit requires its actual beneficiary class."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('nova-standard-infinity-player', 'Scythe', 'Sorceress', None, '334:0', 'nova-sorceress-guide', 1),
    ('nova-hybrid-infinity-merc', 'Giant Thresher', 'Sorceress', 'Act 2 Might', '151:123', 'nova-sorceress-guide', 3),
    ('lightning-strike-infinity-player', 'Matriarchal Spear', 'Amazon', None, '334:0', 'lightning-strike-amazon', 1),
)


def cases():
    for role, base, cls, merc, key, build, variant in SPECS:
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Infinity',
                ((151, 123, 12), (334, 0, 45), (17, 0, 255), (18, 0, 255), (194, 0, 4)),
                ethereal=merc is not None,
                sockets=4,
                socket_contents='filled',
                runeword='Infinity',
                socket_items=tuple(SocketItem(n + ' Rune') for n in ('Ber', 'Mal', 'Ber', 'Ist')),
            )
            for label, player, usable in [
                ('correct-class', cls, True),
                ('wrong-class', 'Paladin', False),
                ('unknown-class', None, False),
            ]:
                yield Case(
                    id=f'infinity-class/{role}/{quality}/{label}',
                    item=item,
                    context={'player_class': player, 'mercenary_type': merc},
                    covers=(role,),
                    scenario='positive' if usable else 'unknown' if player is None else 'negative',
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
                    absent_stat_configurations={'334:0': (role + '-stats',)} if merc else {},
                    evidence=(
                        f'pricing/data/wp-a-variants/{build}.json:/variants/{variant}',
                        'third-parties/d2data/json/runes.json:/Infinity',
                    ),
                )


CASES = tuple(cases())
