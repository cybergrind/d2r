"""Named gear stays useful while the explicitly required filler is unconfirmed."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('berserk-barbarian-4-stormshield', 'Barbarian', 'Stormshield', 'Monarch', 'unique', ('Shael Rune',)),
    ('lightning-sorceress-3-stormshield', 'Sorceress', 'Stormshield', 'Monarch', 'unique', ('Shael Rune',)),
    ('meteor-sorceress-4-stormshield', 'Sorceress', 'Stormshield', 'Monarch', 'unique', ('Um Rune',)),
    (
        'dragon-talon-assassin-stormlash-qualified-equipment',
        'Assassin',
        'Stormlash',
        'Scourge',
        'unique',
        ('Shael Rune',),
    ),
    (
        'zeal-paladin-griswold-s-honor-named-shield-tail',
        'Paladin',
        "Griswold's Honor",
        'Vortex Shield',
        'set',
        ('Ist Rune',) * 3,
    ),
)


SOURCES = {
    'berserk-barbarian-4-stormshield': 'pricing/data/wp-a-builds.json:/berserk-barbarian/variants/4',
    'lightning-sorceress-3-stormshield': 'pricing/data/wp-a-builds.json:/lightning-sorceress/variants/3',
    'meteor-sorceress-4-stormshield': 'pricing/data/wp-a-builds.json:/meteor-sorceress/variants/4',
    'dragon-talon-assassin-stormlash-qualified-equipment': (
        'pricing/data/wp-a-builds.json:/dragon-talon-assassin/slots/Weapon/1'
    ),
    'zeal-paladin-griswold-s-honor-named-shield-tail': (
        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/32'
    ),
}


def cases():
    for role, klass, name, base, quality, runes in SPECS:
        item = Item(
            base,
            quality,
            name,
            sockets=len(runes),
            socket_contents='filled',
            socket_items=tuple(SocketItem(rune) for rune in runes),
        )
        variants = [
            ('ready', item, 'true', 'true', 'positive'),
            ('empty', replace(item, socket_contents='empty', socket_items=()), 'true', 'false', 'negative'),
            (
                'wrong-runes',
                replace(item, socket_items=(SocketItem('El Rune'),) * len(runes)),
                'true',
                'false',
                'negative',
            ),
            ('unread-runes', replace(item, socket_items=()), 'true', 'unknown', 'unknown'),
            ('ethereal', replace(item, ethereal=True), 'false', 'true', 'negative'),
        ]
        if name != "Griswold's Honor":
            variants.append(
                (
                    'unsocketed',
                    replace(item, sockets=0, socket_contents='empty', socket_items=()),
                    'true',
                    'false',
                    'negative',
                )
            )
        for label, candidate, required, payload, scenario in variants:
            yield Case(
                id=f'named-socket-preparation/{role}/{label}',
                item=candidate,
                context={'player_class': klass},
                covers=(role,),
                scenario=scenario,
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                status='failed' if required == 'false' else 'partial',
                                rule_trace=IsPartialDict(truth=required),
                                dependencies=Contains(IsPartialDict(status=payload)),
                            )
                        )
                    )
                },
                report_contains=(name,)
                + (
                    (f'Needs: Actual linked {runes[0]}',)
                    if role == 'berserk-barbarian-4-stormshield' and label in ('empty', 'wrong-runes', 'unsocketed')
                    else ()
                )
                + (
                    ('Check: Actual linked Shael Rune',)
                    if role == 'berserk-barbarian-4-stormshield' and label == 'unread-runes'
                    else ()
                ),
                evidence=(SOURCES[role],),
            )


CASES = tuple(cases())
