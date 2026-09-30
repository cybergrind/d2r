"""Conservative skill-combination review, 2026-09-27; see SKILL_REVIEW.md.

Groups identify actual uses, not every skill receiving hard points in a build.
Companions improve a qualifying item but never trigger an alert by themselves.
"""

# (primary targets, useful companions). Names resolve through the existing native
# skill catalog, which verifies class and tree; unrelated prefixes never count.
GROUPS = (
    (('Fire Ball', 'Meteor', 'Hydra'), ('Fire Mastery',)),
    (('Enchant',), ('Fire Mastery',)),
    (('Lightning', 'Chain Lightning', 'Nova'), ('Lightning Mastery',)),
    (('Blizzard', 'Frozen Orb'), ('Cold Mastery',)),
    (('Energy Shield',), ()),
    (('Poison Nova',), ('Corpse Explosion', 'Lower Resist')),
    (('Bone Spear', 'Bone Spirit'), ('Corpse Explosion',)),
    (('Raise Skeleton',), ('Skeleton Mastery', 'Raise Skeletal Mage', 'Revive')),
    (('Blessed Hammer',), ('Concentration',)),
    (('Fist of the Heavens',), ('Holy Bolt', 'Conviction')),
    (('Battle Orders', 'War Cry', 'Find Item'), ('Shout', 'Battle Command')),
    (('Fissure', 'Volcano', 'Armageddon'), ()),
    (('Tornado', 'Hurricane'), ('Oak Sage',)),
    (('Raven', 'Summon Grizzly'), ('Summon Dire Wolf', 'Summon Spirit Wolf', 'Heart of Wolverine')),
    (('Lightning Sentry',), ('Death Sentry', 'Weapon Block', 'Fade', 'Burst of Speed')),
    (('Wake of Fire', 'Fire Blast'), ('Weapon Block', 'Fade', 'Death Sentry')),
    (('Fade', 'Venom'), ()),
    (
        ('Hex: Purge', 'Eldritch Blast', 'Echoing Strike', 'Mirrored Blades'),
        ('Levitation Mastery', 'Consume', 'Bind Demon', 'Demonic Mastery', 'Hex: Bane'),
    ),
    (('Abyss', 'Miasma Chain'), ('Bind Demon', 'Consume', 'Enhanced Entropy')),
    (('Apocalypse', 'Flame Wave', 'Ring of Fire'), ('Enhanced Entropy', 'Sigil: Death')),
)
PRIMARY_SKILLS = frozenset(name for primary, _ in GROUPS for name in primary)


def companions(name):
    return frozenset(
        other for primary, extra in GROUPS if name in primary for other in (*primary, *extra) if other != name
    )
