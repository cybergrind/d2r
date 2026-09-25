"""Verified Rainbow Facet event projections; skill/level remain identity constraints."""

from pricing.knowledge.assessment.mechanics.poison import POISON_KEYS, fixed_poison_total


# Native table and skill IDs verified against local definitions/metadata; market
# fields against appraisal-properties.json. Values are chance, not spell level.
TRIGGERS = {
    392: (197, 53, '780', 'Chain Lightning'),
    393: (197, 59, '781', 'Blizzard'),
    394: (197, 56, '782', 'Meteor'),
    395: (197, 92, '784', 'Poison Nova'),
    396: (199, 48, '785', 'Nova'),
    397: (199, 44, '786', 'Frost Nova'),
    398: (199, 46, '787', 'Blaze'),
}


def facet_trigger(facts, definition):
    if facts.name != 'Rainbow Facet':
        return {}, set(), []
    spec = TRIGGERS.get(definition.get('table_id'))
    if spec is None:
        return {}, set(), ['Facet trigger has no verified market chance field.']
    stat, skill, market, name = spec
    game = definition['game_definition']
    level, chance = game.get('max4'), game.get('min4')
    event = 'death-skill' if stat == 197 else 'levelup-skill'
    if (
        game.get('prop4') != event
        or game.get('par4') != name
        or type(level) is not int
        or not 0 < level < 64
        or chance != 100
    ):
        return {}, set(), ['Facet trigger definition changed; projection requires review.']
    key = f'{stat}:{skill * 64 + level}'
    row = facts.stats.get(key, {})
    triggers = {k for k in facts.stats if k.split(':')[0] in ('197', '199')}
    if (
        triggers != {key}
        or row.get('status') != 'decoded'
        or type(row.get('value')) not in (int, float)
        or row['value'] != chance
    ):
        return {}, set(), ['Facet death/level-up trigger does not match the selected skill, level and chance.']
    return {market: chance}, {key}, []


def facet_fixed_damage(facts, definition):
    """Permit omitted fixed endpoints only after both captured values are verified."""
    if facts.name != 'Rainbow Facet':
        return {}, []
    game = definition['game_definition']
    pair = {
        'dmg-fire': ((48, '458'), (49, '459')),
        'dmg-ltng': ((50, '478'), (51, '479')),
        'dmg-cold': ((54, '482'), (55, '483')),
    }.get(game.get('prop1'))
    if pair is None:
        return {}, []  # Poison rates require a separate policy.
    properties, gaps = {}, []
    for (stat, prop), field in zip(pair, ('min1', 'max1'), strict=True):
        expected = game.get(field)
        row = facts.stats.get(f'{stat}:0', {})
        if (
            type(expected) is not int
            or row.get('status') != 'decoded'
            or type(row.get('value')) not in (int, float)
            or row['value'] != expected
            or type(facts.properties.get(prop)) not in (int, float)
            or facts.properties[prop] != expected
        ):
            gaps.append(f'Facet fixed damage {stat}:0 is missing, changed or unverified.')
        else:
            properties[prop] = expected
    return properties, gaps


def facet_fixed_duration(facts, definition):
    """dmg-cold Parameter is frames, per local properties.json / PropertyFunc17."""
    game = definition['game_definition']
    if facts.name != 'Rainbow Facet' or game.get('prop1') != 'dmg-cold':
        return set(), []
    frames = game.get('par1')
    row = facts.stats.get('56:0', {})
    if (
        type(frames) is not int
        or frames <= 0
        or row.get('status') != 'decoded'
        or type(row.get('raw')) is not int
        or row['raw'] != frames
        or row.get('unit') != 'seconds'
        or type(row.get('value')) not in (int, float)
        or row['value'] != frames / 25
    ):
        return set(), ['Facet fixed cold duration is missing, changed or unverified.']
    return {'56:0'}, []


def facet_fixed_poison(facts, definition):
    """Verify the single fixed source before projecting its rounded tooltip total.

    Native PropertyFuncs15/16/17 store min/max rates and frame length directly
    (poison stats have no ValShift); adding poison maximum adds one source.
    Market field589 is total Poison Damage, not the native damage-per-frame rate.
    """
    game = definition['game_definition']
    if facts.name != 'Rainbow Facet' or game.get('prop1') != 'dmg-pois':
        return {}, set(), []
    low, high, frames = (game.get(k) for k in ('min1', 'max1', 'par1'))
    gap = ['Facet fixed poison rates, duration or source count are missing, changed or unverified.']
    total = fixed_poison_total(facts, low, high, frames)
    if total is None:
        return {}, set(), gap
    return {'589': total}, set(POISON_KEYS), []
