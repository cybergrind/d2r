"""Source-specific four-facet shields, using real unique socket identities."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Native uniqueitems 392-399; property stat IDs verified in properties/itemstatcost.
ELEMENTS = {
    'lightning': (330, 334, 392, 396, ((50, 0, 1), (51, 0, 74)), (53, 47), (48, 41)),
    'cold': (331, 335, 393, 397, ((54, 0, 24), (55, 0, 38), (56, 0, 3)), (59, 37), (44, 43)),
    'fire': (329, 333, 394, 398, ((48, 0, 17), (49, 0, 45)), (56, 31), (46, 29)),
    'poison': (332, 336, 395, 399, ((57, 0, 187), (58, 0, 187), (59, 0, 50), (326, 0, 1)), (92, 51), (278, 23)),
}
SPECS = (
    ('blizzard-sorceress-main-shield', 'Sorceress', 'cold', 3),
    ('blizzard-sorceress-main-swap', 'Sorceress', 'cold', 3),
    ('blizzard-sorceress-standard-swap', 'Sorceress', 'cold', 3),
    ('lightning-fury-amazon-guide-main-shield', 'Amazon', 'lightning', 3),
    ('lightning-fury-amazon-guide-ubers-shield', 'Amazon', 'lightning', 3),
    ('fissure-druid-main-shield', 'Druid', 'fire', 5),
    ('lightning-strike-amazon-main-shield', 'Amazon', 'lightning', 5),
    ('poison-nova-necromancer-main-shield', 'Necromancer', 'poison', 5),
    ('lightning-sentry-assassin-main-shield', 'Assassin', 'lightning', 3),
    ('lightning-sentry-assassin-main-swap', 'Assassin', 'lightning', 3),
    ('lightning-sorceress-main-shield', 'Sorceress', 'lightning', 5),
)


SOURCE_LOCATORS = {
    'blizzard-sorceress-main-shield': '/blizzard-sorceress/slots/Off-Hand/2',
    'blizzard-sorceress-main-swap': '/blizzard-sorceress/slots/Off-Hand-Swap/3',
    'blizzard-sorceress-standard-swap': '/blizzard-sorceress/variants/1/player/Off-Hand Swap/0',
    'lightning-fury-amazon-guide-main-shield': '/lightning-fury-amazon-guide/slots/Off-Hand/3',
    'lightning-fury-amazon-guide-ubers-shield': '/lightning-fury-amazon-guide/variants/3/player/Off-Hand/0',
    'fissure-druid-main-shield': '/fissure-druid/slots/Off-Hand/1',
    'lightning-strike-amazon-main-shield': '/lightning-strike-amazon/slots/Off-Hand/4',
    'poison-nova-necromancer-main-shield': '/poison-nova-necromancer/slots/Off-Hand/9',
    'lightning-sentry-assassin-main-shield': '/lightning-sentry-assassin/slots/Off-Hand/2',
    'lightning-sentry-assassin-main-swap': '/lightning-sentry-assassin/slots/Off-Hand-Swap/1',
    'lightning-sorceress-main-shield': '/lightning-sorceress/slots/Off-Hand/3',
}


def facet(element, roll, *, up=False):
    mastery, pierce, die_id, up_id, fixed, die_skill, up_skill = ELEMENTS[element]
    skill, level = up_skill if up else die_skill
    return SocketItem(
        'Jewel',
        (*fixed, (mastery, 0, roll), (pierce, 0, roll), (199 if up else 197, skill * 64 + level, 100)),
        complete=True,
        name='Rainbow Facet',
        unique_table_id=up_id if up else die_id,
    )


def cases():
    for slug, klass, element, minimum in SPECS:
        role = slug + '-facet-shield-filled'
        mastery, pierce = ELEMENTS[element][:2]
        mixed = slug.endswith('ubers-shield')
        children = (
            (facet(element, 5),) + (facet(element, minimum, up=True),) * 3 if mixed else (facet(element, minimum),) * 4
        )
        total = minimum * 4 + (5 - minimum if mixed else 0)
        raw = ((20, 0, 20), (102, 0, 30), (mastery, 0, total), (pierce, 0, total), (194, 0, 4))
        item = Item('Monarch', 'magic', raw_stats=raw, sockets=4, socket_contents='filled', socket_items=children)
        variants = [
            ('native', item, klass, True),
            (
                'wrong-element',
                replace(item, socket_items=(facet('fire' if element != 'fire' else 'cold', 5),) * 4),
                klass,
                False,
            ),
            (
                'weak-fourth',
                replace(item, socket_items=(*children[:3], facet(element, minimum - 1, up=mixed))),
                klass,
                False,
            ),
            ('missing-fourth', replace(item, socket_items=children[:3]), klass, False),
            (
                'ordinary-jewels',
                replace(
                    item, socket_items=(SocketItem('Jewel', ((mastery, 0, 5), (pierce, 0, 5)), complete=True),) * 4
                ),
                klass,
                False,
            ),
            ('empty', replace(item, socket_contents='empty', socket_items=()), klass, False),
            ('low-block', replace(item, raw_stats=((20, 0, 19), *raw[1:])), klass, False),
            ('low-fbr', replace(item, raw_stats=tuple((s, p, 29 if s == 102 else v) for s, p, v in raw)), klass, False),
            ('wrong-class', item, 'Warlock', False),
            ('ethereal', replace(item, ethereal=True), klass, False),
            ('unknown-ethereal', replace(item, ethereal=None), klass, False),
            ('normal', replace(item, rarity='normal'), klass, False),
        ]
        if mixed:
            variants.append(('wrong-trigger-mix', replace(item, socket_items=(facet(element, 5),) * 4), klass, False))
        else:
            variants.append(
                ('level-up-variant', replace(item, socket_items=(facet(element, minimum, up=True),) * 4), klass, True)
            )
        for label, candidate, player, active in variants:
            yield Case(
                id=f'facet-shield/{slug}/{label}',
                item=candidate,
                context={'player_class': player},
                covers=(f'role:{role}:magic',),
                scenario='positive'
                if active
                else 'unknown'
                if label in ('missing-fourth', 'unknown-ethereal')
                else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                    for key in ('20:0', '102:0', f'{mastery}:0', f'{pierce}:0')
                                }
                            )
                        )
                    )
                }
                if active
                else {},
                absent_configurations=() if active else (role + '-stats',),
                report_contains=('Monarch', 'Rainbow Facet') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + SOURCE_LOCATORS[slug],
                    'third-parties/d2data/json/uniqueitems.json:392-399',
                ),
            )


CASES = tuple(cases())
