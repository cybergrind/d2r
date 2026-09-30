"""Typed source reviews for resolved charm bases and their magic-item patterns."""

from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


# Verified against third-parties/d2data/json/misc.json. Named/renewed charms
# follow their own identity contracts; this map is only the three magic bases.
CHARM_BASES = {
    'Small Charm': ('cm1', 'scha'),
    'Large Charm': ('cm2', 'mcha'),
    'Grand Charm': ('cm3', 'lcha'),
}


def identity_supported(occurrence):
    return (
        occurrence.get('identity_status') == 'resolved'
        and occurrence.get('category') == 'misc'
        and occurrence.get('name') in CHARM_BASES
        and occurrence.get('side') == 'player'
        and occurrence.get('slot') == 'Charms'
    )


def branch_matches(role, occurrence):
    if not identity_supported(occurrence):
        return False
    code, item_type = CHARM_BASES[occurrence['name']]
    return (
        not role.get('names')
        and role.get('types') == [item_type]
        and role.get('qualities') == ['magic']
        and requires_eq(role.get('must', {}), 'fact_eq', 'base_code', code)
    )
