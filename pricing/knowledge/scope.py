"""The one Traderie scope predicate: Softcore / Non-Ladder / PC / Reign of the Warlock (AGENTS.md rule 1).

Standard library only, so the `pricing/tools` scripts can import it under a plain `python3`.
"""

VERSION = 'reign of the warlock'
OTHER_VERSIONS = frozenset({'classic', 'classic (base game)', 'lord of destruction'})
EXPECTED = {'799': 'softcore', '800': False, '798': 'PC'}


def property_values(raw):
    """Traderie array-valued metadata is serialized in its string field."""
    return {str(p['property_id']): p.get(p['type'] if p['type'] in ('number', 'bool') else 'string') for p in raw}


def scope_status(properties):
    """Return verified, rejected, or unknown; absent scope is never accepted."""
    if '800' in properties and properties['800'] is not False:
        return 'rejected'
    if any(key in properties and properties[key] != value for key, value in EXPECTED.items()):
        return 'rejected'
    versions = {part.strip().lower() for part in str(properties.get('1854', '')).split(',')}
    if VERSION not in versions:
        return 'rejected' if versions & OTHER_VERSIONS else 'unknown'
    return 'verified' if all(key in properties for key in EXPECTED) else 'unknown'


def listing_scope(listing):
    """scope_status of a raw Traderie listing (its `properties` array)."""
    return scope_status(property_values(listing.get('properties') or []))


def in_scope(listing):
    """Only a verified listing counts as evidence; unknown scope is quarantined, not kept."""
    return listing_scope(listing) == 'verified'
