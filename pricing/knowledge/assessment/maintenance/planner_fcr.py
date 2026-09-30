"""Native-checked FCR lower bounds from a planner's active equipment only.

Missing scalar entries contribute zero only when their complete native/affix
definition has no FCR. Socket bonuses are checked for nonnegative FCR but omitted
from the lower bound. This is source evidence, not a live character-state claim.
"""

from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import ancestors


SOURCE_PATHS = {
    'game': 'pricing/raw/mr/planners/game-data.json',
    'metadata': 'inventory_tracking/items/data/item_metadata.json',
    'uniques': 'third-parties/d2data/json/uniqueitems.json',
    'runes': 'third-parties/d2data/json/runes.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'weapons': 'third-parties/d2data/json/weapons.json',
    'types': 'third-parties/d2data/json/itemtypes.json',
    'properties': 'third-parties/d2data/json/properties.json',
    'stats': 'third-parties/d2data/json/itemstatcost.json',
    'misc': 'third-parties/d2data/json/misc.json',
    'gems': 'third-parties/d2data/json/gems.json',
}


ACTIVE = frozenset({'head', 'neck', 'tors', 'rarm', 'larm', 'glov', 'belt', 'feet', 'lrin', 'rrin'})
SWAP = frozenset({'rarm2', 'larm2'})
STAT = 'item_fastercastrate'


def cast_property(code, tables):
    # Planner exports capitalize some native property tokens (Gethit-skill).
    code = code.lower() if isinstance(code, str) else code
    if code and code not in tables['properties']:
        raise ValueError('FCR property definition is unknown')
    prop = tables['properties'].get(code, {})
    return prop.get('stat1') == STAT


def scalar_bounds(row, tables, *, code_prefix, low_prefix, high_prefix, count):
    low = high = 0
    for i in range(1, count + 1):
        if cast_property(row.get(f'{code_prefix}{i}'), tables):
            a, b = row.get(f'{low_prefix}{i}'), row.get(f'{high_prefix}{i}')
            if type(a) is not int or type(b) is not int or not 0 <= a <= b:
                raise ValueError('FCR native scalar bounds invalid')
            low += a
            high += b
    return low, high


def native_recipe(item, tables):
    identifier = item.get('unique', '')
    if not isinstance(identifier, str) or not identifier.startswith('runeword') or not identifier[8:].isdecimal():
        raise ValueError('FCR planner runeword identifier invalid')
    codes = item.get('socketedItems')
    if not isinstance(codes, list) or not codes or item.get('sockets') != len(codes):
        raise ValueError('FCR runeword payload missing or inconsistent')
    bases = [table[item['base']] for table in (tables['armor'], tables['weapons']) if item.get('base') in table]
    if len(bases) != 1 or bases[0].get('gemsockets', 0) < len(codes):
        raise ValueError('FCR runeword native base is incompatible')
    types = ancestors(bases[0].get('type'), tables['types'])
    matches = []
    for name, recipe in tables['runes'].items():
        runes = [recipe[f'Rune{i}'] for i in range(1, 7) if recipe.get(f'Rune{i}')]
        allowed = {recipe[f'itype{i}'] for i in range(1, 7) if recipe.get(f'itype{i}')}
        excluded = {recipe[f'etype{i}'] for i in range(1, 4) if recipe.get(f'etype{i}')}
        if recipe.get('complete') == 1 and runes == codes and types & allowed and not types & excluded:
            matches.append((name, recipe))
    if len(matches) != 1:
        raise ValueError('FCR runeword identity requires one legal ordered native recipe')
    name, recipe = matches[0]
    # Old planner tables omit RotW entries. Known entries must still agree.
    legacy = tables['game']['runes'].get(item.get('unique'))
    if legacy and legacy.get('name') != recipe.get('Name'):
        raise ValueError('FCR planner/native runeword identities conflict')
    return name, scalar_bounds(recipe, tables, code_prefix='T1Code', low_prefix='T1Min', high_prefix='T1Max', count=7)


def affix_fcr(item, tables):
    if not item.get('mods'):
        raise ValueError('FCR affixed item source is incomplete')
    total = 0
    for key, values in item.get('mods', {}).items():
        table = 'magicPrefix' if key.startswith('mp') else 'magicSuffix' if key.startswith('ms') else None
        definition = tables['game'].get(table, {}).get(key) if table else None
        if not definition or not isinstance(values, list):
            raise ValueError('FCR affix source missing')
        total += rolled_fcr(definition, values, tables)
    crafted = item.get('crafted', {})
    if item.get('quality') == 8 and len(crafted) != 1:
        raise ValueError('FCR crafted item needs its complete craft source')
    for key, values in crafted.items():
        definition = tables['game']['crafted'].get(key)
        base = tables['misc'].get(item.get('base'), {})
        types = ancestors(base.get('type'), tables['types'])
        if not definition or not isinstance(values, list) or definition.get('input1', '').split(',')[0] not in types:
            raise ValueError('FCR craft source or base invalid')
        total += rolled_fcr(definition, values, tables)
    return item.get('name', 'Affixed item'), (total, total)


def rolled_fcr(definition, values, tables):
    positions = [i for i in range(1, 4) if definition.get(f'mod{i}code')]
    if len(values) != len(positions):
        raise ValueError('FCR affix/craft roll vector incomplete')
    total = 0
    for position, value in zip(positions, values, strict=True):
        low, high = definition.get(f'mod{position}min'), definition.get(f'mod{position}max')
        if type(value) is not int or type(low) is not int or type(high) is not int or not low <= value <= high:
            raise ValueError('FCR affix/craft roll outside source bounds')
        if cast_property(definition[f'mod{position}code'], tables):
            if value < 0:
                raise ValueError('FCR negative affix contribution unsupported')
            total += value
    return total


def contribution(item, tables):
    quality = item.get('quality')
    if quality == 7:
        name, bounds = native_recipe(item, tables)
    elif quality == 6:
        identifier = item.get('unique', '')
        key = identifier.removeprefix('unique')
        definition = tables['uniques'].get(key)
        identity = tables['metadata']['identities']['unique'].get(key)
        if (
            not identifier.startswith('unique')
            or not definition
            or not identity
            or identity.get('game_definition') != definition
            or item.get('base') != definition.get('code')
        ):
            raise ValueError('FCR unique identity or native base unverified')
        name = identity['name']
        bounds = scalar_bounds(definition, tables, code_prefix='prop', low_prefix='min', high_prefix='max', count=12)
    elif quality in (3, 4, 8):
        name, bounds = affix_fcr(item, tables)
    else:
        raise ValueError('FCR item quality is not supported by this source review')
    observed = item.get('stats', {}).get(STAT)
    if observed is None and bounds == (0, 0):
        return name, 0
    if type(observed) is not int or not bounds[0] <= observed <= bounds[1]:
        raise ValueError('FCR observed scalar differs from its native/affix bounds')
    return name, observed


def check_sockets(item, items, tables, seen):
    for ref in item.get('socketedItems', []):
        if isinstance(ref, str) and ref in tables['gems']:
            gem = tables['gems'][ref]
            for key, code in gem.items():
                if key.endswith('Code') and cast_property(code, tables):
                    low = gem.get(key.removesuffix('Code') + 'Min')
                    if type(low) is not int or low < 0:
                        raise ValueError('FCR socket effect can invalidate the lower bound')
            continue
        key = str(ref)
        if key in seen or key not in items:
            raise ValueError('FCR socket reference missing or recursive')
        child = items[key]
        contribution(child, tables)
        check_sockets(child, items, tables, seen | {key})


def active_fcr_evidence(profile, items, tables):
    cost = tables['stats'].get(STAT, {})
    if cost.get('*ID') != 105 or cost.get('Stat') != STAT:
        raise ValueError('FCR native stat definition changed')
    equipment = profile.get('items', {})
    if set(equipment) - ACTIVE - SWAP:
        raise ValueError('FCR planner equipment slot is unknown')
    active_ids = [str(equipment[slot]) for slot in ACTIVE & equipment.keys()]
    if len(active_ids) != len(set(active_ids)):
        raise ValueError('FCR duplicate active item reference')
    contributors = []
    for slot in sorted(ACTIVE & equipment.keys()):
        item_id = str(equipment[slot])
        item = items.get(item_id)
        if not item:
            raise ValueError('FCR active item reference missing')
        name, value = contribution(item, tables)
        check_sockets(item, items, tables, {item_id})
        if value:
            contributors.append({'slot': slot, 'item_id': item_id, 'name': name, 'fcr': value})
    return {'minimum_fcr': sum(row['fcr'] for row in contributors), 'contributors': contributors}
