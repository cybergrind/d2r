"""Original Sunder listing magnitudes projected onto native signed trade rolls."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.mechanics.sunder import PENALTIES, listing_penalties
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_named_aliases import ORIGINAL_SUNDERS


MODE = 'original_sunder'


def project_properties(review, row, mapping):
    mode = review.get('sunder_penalty')
    if mode is None:
        return dict(row['properties'])
    name = row.get('name')
    if (
        mode != MODE
        or row.get('rarity') != 'unique'
        or name not in PENALTIES
        or ORIGINAL_SUNDERS.get(row.get('catalog_id')) != name
    ):
        raise ValueError('Unverified Sunder trade catalog identity or representation')
    stat, _ = PENALTIES[name]
    prop = metadata()['stats'][str(stat)]['property_id']
    if mapping != {f'{stat}:0': prop}:
        raise ValueError('Unverified Sunder trade material mapping')
    spec = catalog().named['unique', name]['roll_ranges'][str(stat)]
    contract = {'policy': 'named', 'rarity': 'unique', 'name': name, 'properties': {prop: spec['max']}}
    properties = listing_penalties(contract, row, row['properties'])
    value = properties.get(prop)
    if type(value) is not int or not spec['min'] <= value <= spec['max'] < 0:
        raise ValueError('Missing or invalid Sunder trade penalty')
    return properties
