"""Reviewed Opalvein elemental cohorts retain their single random modifier."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.property_groups import selected_ranges


MODE = 'opalvein_elemental'
ELEMENTAL_KEYS = {'329:0', '331:0', '330:0'}


def valid_reviewed_choice(review, facts, *, market_properties=None):
    mode = review.get('property_choice')
    return mode is None or (
        mode == MODE and valid_choice(facts, market_properties=market_properties, allowed=reviewed_keys(review))
    )


def reviewed_keys(review):
    keys = review.get('choice_keys', tuple(ELEMENTAL_KEYS))
    if not isinstance(keys, (list, tuple)) or not keys or len(keys) != len(set(keys)) or set(keys) - ELEMENTAL_KEYS:
        raise ValueError('Unverified trade evidence elemental choice keys')
    return frozenset(keys)


def validate_cohorts(review):
    if review.get('property_choice') != MODE:
        if 'choice_keys' in review:
            raise ValueError('Unverified trade evidence elemental choice keys')
        return
    for key in reviewed_keys(review):
        prop = metadata()['stats'][key.split(':')[0]]['property_id']
        sellers = {r['seller_id'] for r in review['market_evidence'] if prop in r['properties']}
        if len(sellers) < 3:
            raise ValueError('Insufficient independent elemental choice evidence')


def valid_choice(facts, *, market_properties=None, allowed=ELEMENTAL_KEYS):
    if (facts.rarity, facts.name) != ('unique', 'Opalvein'):
        return False
    if market_properties is None and (facts.capture_complete is not True or facts.gaps):
        return False
    definition, errors = resolve_named_definition(facts, identity_only=True)
    if errors or definition is None:
        return False
    groups = definition.get('property_groups', ())
    if len(groups) != 1 or groups[0]['code'] != 'magdam-rand':
        return False
    selected = selected_ranges(groups[0], facts.stats)
    if selected is None or len(selected) != 1 or not set(selected) <= allowed:
        return False
    if market_properties is not None:
        # Unsupported alternatives are deliberately not projected into material
        # trade stats, but their source fields must still reject mixed choices.
        specs = metadata()['stats']
        choice_properties = set()
        for choice in groups[0]['choices']:
            ranges = choice['roll_ranges']
            if set(ranges) == {'17', '18'} and choice['property'] == 'dmg%':
                choice_properties.add('510')
            else:
                for roll in ranges.values():
                    prop = specs.get(str(roll['stat_id']), {}).get('property_id')
                    if prop is None:
                        return False
                    choice_properties.add(prop)
        key = next(iter(selected))
        expected = specs[key.split(':')[0]]['property_id']
        if choice_properties.intersection(market_properties) != {expected}:
            return False
    return True
