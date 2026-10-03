"""Shared impossible variants for verified jewelry, charm and jewel base identities.

Reviewed against pricing/raw/d2data/misc.json and itemtypes.json (2026-09-24).
These named base families have no durability and no socket capacity; this rule
must not be generalized to indestructible equipment or unknown identities.
"""

CATALOGS = frozenset(
    {
        ('Ring', 'misc'),
        ('Amulet', 'misc'),
        ('Small Charm', 'charms'),
        ('Large Charm', 'charms'),
        ('Grand Charm', 'charms'),
        ('Crafted Sunder Charm', 'charms'),
        ('Jewel', 'jewels'),
        ('Colossal Jewel', 'jewels'),
    }
)
BASE_NAMES = frozenset(name for name, _ in CATALOGS)
EXPECTED = (('sockets', '402', 0), ('ethereal', '738', False), ('socket_contents', '934', 'empty'))
