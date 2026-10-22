"""The paid skills a class item's staffmod counts with, 2026-10-22; see SKILL_REVIEW.md.

The triage's list (pricing/triage/import_class_rules.py PAID_SKILLS: the best skill on the +5 listings of two or more
priced sellers, 2026-10-08 cache), the claws' Death Sentry, Wake of Fire and Phoenix Strike (the player, 2026-10-20)
and the Warlock's (pricing.html §7, inventory_tracking/loot/build_wants.py WARLOCK_PAID). A skill nobody pays for
(Raise Skeleton, Fissure, Raven, Find Item, Mirrored Blades, Flame Wave, Ring of Fire) never alerts; another paid
skill of its tree on the item is named as a companion.
"""

PAID = {
    'Barbarian': ('Battle Orders', 'Battle Command', 'War Cry', 'Grim Ward', 'Increased Speed'),
    'Druid': (
        'Tornado', 'Armageddon', 'Hurricane', 'Volcano', 'Summon Grizzly', 'Fury', 'Shock Wave', 'Fire Claws',
    ),
    'Necromancer': ('Poison Nova', 'Bone Spirit', 'Bone Spear'),
    'Sorceress': (
        'Chain Lightning', 'Lightning', 'Nova', 'Lightning Mastery', 'Thunder Storm', 'Energy Shield', 'Enchant',
        'Fire Ball', 'Hydra', 'Meteor', 'Fire Wall', 'Fire Mastery', 'Blizzard', 'Frozen Orb', 'Cold Mastery',
    ),
    'Paladin': ('Fist of the Heavens', 'Blessed Hammer'),
    'Assassin': ('Lightning Sentry', 'Death Sentry', 'Wake of Fire', 'Phoenix Strike', 'Venom', 'Fade'),
    'Warlock': (
        'Abyss', 'Hex: Purge', 'Echoing Strike', 'Eldritch Blast', 'Apocalypse', 'Summon Tainted', 'Summon Defiler',
        'Consume', 'Bind Demon', 'Sigil: Death', 'Miasma Chain', 'Blood Boil', 'Blade Warp',
    ),
}  # fmt: skip
PRIMARY_SKILLS = frozenset(name for names in PAID.values() for name in names)


def companions(name):
    """The other paid skills of `name`'s class."""
    return frozenset(other for names in PAID.values() if name in names for other in names if other != name)
