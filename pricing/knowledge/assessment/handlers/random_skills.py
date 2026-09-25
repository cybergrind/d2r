"""Required randomly selected skill bonuses that scalar ranges cannot represent."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.adapters.market_projection import market_properties


# Wraithstep's cached game definition uses skilltab-war, min=max=1.
# Native stat188 uses class*8+tree: Warlock Demon/Eldritch/Chaos are56/57/58.
RANDOM_SKILL_KEYS = {'skilltab-war': ('188:56', '188:57', '188:58')}


def comparison_gaps(facts, definition, *, require_projection=True):
    record = definition.get('game_definition', {})
    gaps = []
    for slot in range(1, 13):
        code = record.get(f'prop{slot}')
        keys = RANDOM_SKILL_KEYS.get(code)
        low, high = record.get(f'min{slot}'), record.get(f'max{slot}')
        if code == 'randclassskill':
            # Native properties.json func36: min/max choose the class;
            # val1=3 supplies the skill bonus, not the selected class ID.
            if type(low) is not int or type(high) is not int or not 0 <= low <= high < len(CLASS_NAMES):
                gaps.append('Random class definition has invalid class ID bounds.')
                continue
            keys = tuple(f'83:{class_id}' for class_id in range(low, high + 1))
            low = high = 3
        if code == 'skill-rand':
            # properties.json func12: min/max select skill ID; par is bonus.
            # D2MOO ITEMMODS_PropertyFunc12 confirms inclusive ID selection.
            if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 4095:
                gaps.append('Random skill definition has invalid skill ID bounds.')
                continue
            keys = tuple(f'107:{skill}' for skill in range(low, high + 1))
            low = high = record.get(f'par{slot}')
        if keys is None:
            continue
        stat_prefix = keys[0].split(':')[0] + ':'
        present = [(key, row) for key, row in facts.stats.items() if key.startswith(stat_prefix)]
        if not facts.capture_complete or len(present) != 1:
            gaps.append('Random skill bonus requires one selected skill or tree in a complete capture.')
            continue
        key, row = present[0]
        value = row.get('value')
        if (
            key not in keys
            or row.get('status') != 'decoded'
            or type(value) not in (int, float)
            or type(low) is not int
            or type(high) is not int
            or not low <= value <= high
        ):
            gaps.append('Random skill bonus is unresolved or outside its native range.')
            continue
        if require_projection:
            property_id = market_properties().get(key)
            if property_id is None or facts.properties.get(property_id) != value:
                gaps.append('Random skill bonus has no matching market projection.')
    return gaps
