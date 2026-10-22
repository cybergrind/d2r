"""One really good vendor buy per class the watcher shows, and the noise it no longer shows ("notify on a really good
items ... not just any +2 skills", the player, 2026-10-22). Asks are the scoped Traderie caches (SC/NL/PC/RotW)."""

import pytest

from inventory_tracking.shop.rules import match_item
from tests.inventory_tracking.shop.test_rules import observation, skill


IAS, FCR, LIFE, SOCKETS, BLOCK, FBR, MF = 93, 105, 7, 194, 20, 102, 80


def tree(layer, level=3):
    return (188, layer, level)


def plus_class(class_id, level=2):
    return (83, class_id, level)


def staffmod(name, level=3):
    return (107, skill(name), level)


EXAMPLES = [
    # Amazon: +3 Javelin and Spear / 20 IAS gloves, asks median 11.4 Ist (5 sellers, 2026-08-19..09-19)
    ('Amazon', 'Chain Gloves', [tree(2), (IAS, 0, 20)], '+3 Javelin and Spear Skills / 20 IAS gloves'),
    # Amazon: +5 Javelin (automod + Lancer's) / 40 IAS Maiden Javelin, 3-6 Jah (7 sellers, 2026-10-03/04)
    ('Amazon', 'Maiden Javelin', [tree(2, 5), (IAS, 0, 40)], '+5 Javelin and Spear Skills / 40 IAS javelin'),
    # Sorceress: +3 Fire / +3 Enchant orb, +6 Enchant asks Q1 57 (7 sellers)
    ('Sorceress', 'Eldritch Orb', [tree(8), staffmod('Enchant')], '+6 Enchant (+3 Fire Skills +3 staffmod)'),
    # Sorceress: +3 Cold / 20 FCR Diadem (Magus), 9 sellers, Q1 11.4 (2026-10-03)
    ('Sorceress', 'Diadem', [tree(10), (FCR, 0, 20)], '+3 Cold Skills / 20 FCR Diadem'),
    # Necromancer: +2 Necromancer / +3 Bone Spear wand, wands +5/+6 9-457 (2026-10-09)
    ('Necromancer', 'Bone Wand', [plus_class(2), staffmod('Bone Spear')], '+5 Bone Spear (+2 Necromancer +3 staffmod)'),
    # Paladin: +2 Paladin / +3 Blessed Hammer scepter, 45.7-188 (2026-10-09)
    (
        'Paladin',
        'War Scepter',
        [plus_class(3), staffmod('Blessed Hammer')],
        '+5 Blessed Hammer (+2 Paladin +3 staffmod)',
    ),
    # Paladin: Jeweler's Sacred Targe of Deflecting, Paladin shields Q1 11.4 (10 sellers)
    (
        'Paladin',
        'Sacred Targe',
        [(SOCKETS, 0, 4), (BLOCK, 0, 20), (FBR, 0, 30)],
        "Jeweler's Sacred Targe of Deflecting (4 sockets / 20 block / 30 FBR)",
    ),
    # Barbarian: +3 Warcries / +3 Battle Orders helm, +6 BO asks Q1 80 (19 sellers)
    ('Barbarian', 'Slayer Guard', [tree(34), staffmod('Battle Orders')], '+6 Battle Orders (+3 Warcries +3 staffmod)'),
    # Druid: +3 Elemental / +3 Tornado pelt, +6 Tornado asks Q1 34 (13 sellers)
    ('Druid', 'Antlers', [tree(42), staffmod('Tornado')], '+6 Tornado (+3 Elemental Skills +3 staffmod)'),
    # Assassin: +3 Traps / +3 Lightning Sentry / 40 IAS claws, 34-377 (2026-09-18), 5 Jah with 40 IAS (10-04)
    (
        'Assassin',
        'Greater Talons',
        [tree(48), staffmod('Lightning Sentry'), (IAS, 0, 40)],
        '+6 Lightning Sentry (+3 Traps +3 staffmod); also 40 IAS',
    ),
    # Assassin: +3 Martial Arts / 20 IAS gloves, asks Q1 4.05 (16 sellers)
    ('Assassin', 'Heavy Gloves', [tree(50), (IAS, 0, 20)], '+3 Martial Arts / 20 IAS gloves'),
    # Warlock: +2 Warlock / +3 Abyss dagger, +2 Warlock daggers with a paid +3 staffmod 11.4 and 15.5 (2026-09-18)
    ('Warlock', 'Kriss', [plus_class(7), staffmod('Abyss')], '+5 Abyss (+2 Warlock +3 staffmod)'),
    # Warlock: +3 Eldritch / 20 FCR circlet, 3 sellers (2026-10-03)
    ('Warlock', 'Circlet', [tree(57), (FCR, 0, 20)], '+3 Eldritch Skills / 20 FCR Circlet'),
    # Any class: Jeweler's of the Whale, 28 sellers, Q1 45.7 on any base tier
    (
        'any',
        'Archon Plate',
        [(SOCKETS, 0, 4), (LIFE, 0, 95 * 256)],
        "Jeweler's Archon Plate of the Whale: 4 sockets + 95 life",
    ),
]


@pytest.mark.parametrize(('who', 'base', 'stats', 'reason'), EXAMPLES, ids=[f'{e[0]}-{e[1]}' for e in EXAMPLES])
def test_a_really_good_buy_of_each_class_alerts(who, base, stats, reason):
    assert reason in match_item(observation(base, stats))


NOISE = [
    # The past alerts (48 of 52 in 2026-10-06..22 were CHECK without a price)
    ('Kriss', [plus_class(7)]),  # +2 Warlock dagger alone: "not kept" (pricing.html §7, 2026-10-21)
    ('Blade', [tree(58)]),  # +3 Chaos alone: median 0.79 (5 sellers)
    ('Kriss', [tree(34)]),  # Echoing +3 Warcries
    ('Kriss', [plus_class(7), (IAS, 0, 40)]),  # IAS does nothing for Echoing Strike (a cast animation)
    ('Coronet', [plus_class(7), (FCR, 0, 20)]),  # +2 class / 20 FCR circlet: Q1 2.6, not kept
    ('Circlet', [plus_class(1)]),
    ('Chain Gloves', [tree(1), (IAS, 0, 20)]),  # +3 Passive / 20 IAS: median 1 (10 sellers)
    ('Chain Gloves', [tree(2, 2), (IAS, 0, 20)]),
    ('Greater Talons', [tree(48), (IAS, 0, 40)]),  # a claw prefix alone is vendor
    ('Greater Talons', [plus_class(6), (IAS, 0, 40)]),
    ('Maiden Javelin', [tree(2, 3), (IAS, 0, 40), plus_class(0, 1)]),  # +1 Amazon: one seller at 4.05
    ('Bone Wand', [plus_class(2), staffmod('Raise Skeleton')]),  # not a paid skill
    ('Antlers', [tree(42), staffmod('Fissure')]),
    ('Monarch', [(SOCKETS, 0, 4), (MF, 0, 20)]),  # a plain 4-socket Monarch: a 22.8 wall
    ('Archon Plate', [(SOCKETS, 0, 4), (MF, 0, 20)]),  # no bare 4-socket Archon is listed
    ('Ancient Armor', [(SOCKETS, 0, 4), (34, 0, 15)]),  # of Amicae: 2 sellers
    ('Ancient Armor', [(SOCKETS, 0, 4), (99, 0, 24)]),  # of Stability: weak
    ('Ancient Armor', [(SOCKETS, 0, 4), (LIFE, 0, 85 * 256)]),  # 81-89 life: 2 sellers
    ('Tiara', [(SOCKETS, 0, 3), (2, 0, 30)]),  # a plain 3-socket Tiara: 5.9-22.8, 3 sellers
]


@pytest.mark.parametrize(('base', 'stats'), NOISE)
def test_the_old_noise_stays_in_the_shop(base, stats):
    assert not match_item(observation(base, stats))
