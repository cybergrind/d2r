"""Original Sunder catalog penalty magnitudes expressed as native signed stats.

The six reviewed catalog identities advertise positive penalty magnitudes in
their cached wph-sunder listings. Their unique definitions only allow negative
resistances. Bone Break instead labels its magnitude as Damage Increased.
This equivalence does not apply to ordinary resistances or other Sunder variants.
"""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_named_aliases import ORIGINAL_SUNDERS


# Cached appraisal-properties labels and uniqueitems penalty stats, 2026-09-25.
PENALTIES = {
    'Cold Rupture': (43, '426'),
    'Flame Rift': (39, '427'),
    'Crack of the Heavens': (41, '428'),
    'Rotting Fissure': (45, '401'),
    'Bone Break': (36, '1223'),
    'Black Cleft': (37, '936'),
}


def listing_penalties(contract, row, properties):
    name = contract['name']
    if (
        contract['policy'] != 'named'
        or contract['rarity'] != 'unique'
        or ORIGINAL_SUNDERS.get(row.get('catalog_id')) != name
        or name not in PENALTIES
    ):
        return properties
    stat, listing_prop = PENALTIES[name]
    native_prop = metadata()['stats'][str(stat)]['property_id']
    spec = catalog().named['unique', name]['roll_ranges'][str(stat)]
    expected = contract['properties'].get(native_prop)
    if type(expected) is not int or not spec['min'] <= expected <= spec['max'] < 0:
        raise ValueError('Sunder penalty is outside its verified native range.')
    result = dict(properties)
    if listing_prop not in result:
        return result
    if listing_prop != native_prop and native_prop in result:
        raise ValueError('Conflicting Sunder damage penalty representations.')
    value = result.pop(listing_prop)
    if type(value) is not int:
        raise ValueError('Sunder penalty must be an integer magnitude.')
    # Resistance fields may explicitly carry the minus sign. Damage Increased
    # is a positive magnitude; negative values there are not damage penalties.
    if listing_prop != native_prop and value <= 0:
        raise ValueError('Sunder damage increase must be positive.')
    value = -abs(value)
    if not spec['min'] <= value <= spec['max']:
        raise ValueError('Listing Sunder penalty is outside its verified range.')
    result[native_prop] = value
    return result
