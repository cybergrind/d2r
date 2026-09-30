"""Cross-check completed planner recipes against pinned native game tables."""

from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


SOURCES = {
    'planner': 'pricing/raw/mr/planners/game-data.json',
    'runes': 'third-parties/d2data/json/runes.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'types': 'third-parties/d2data/json/itemtypes.json',
}

WEAPON_SOURCES = {key: path for key, path in SOURCES.items() if key != 'armor'}
WEAPON_SOURCES['weapons'] = 'third-parties/d2data/json/weapons.json'


def validate_runeword(evidence, role, item, read_json):
    pins = evidence.get('recipe_sources', {})
    sources = WEAPON_SOURCES if 'weapons' in pins else SOURCES
    if set(pins) != set(sources) or any(pins[key].get('path') != path for key, path in sources.items()):
        raise ValueError('Planner runeword requires pinned recipe and base sources')
    weapon = sources is WEAPON_SOURCES
    if weapon and role.get('slot') not in ('Weapon', 'Off-Hand', 'Weapon-Swap', 'Off-Hand-Swap'):
        raise ValueError('Planner runeword weapon requires a weapon equipment slot')
    tables = {key: read_json(pins[key]) for key in sources}
    planner_recipe = tables['planner']['runes'].get(item.get('unique'))
    names = role.get('names', [])
    recipe = tables['runes'].get(names[0]) if len(names) == 1 else None
    if not recipe or not planner_recipe or recipe.get('complete') != 1 or recipe['Name'] != planner_recipe.get('name'):
        raise ValueError('Planner runeword identity differs from native recipe')
    name = names[0]
    if not any(
        ref.get('path') == pins['runes']['path']
        and ref.get('sha256') == pins['runes']['sha256']
        and ref.get('locator') == '/' + name
        for ref in role['source'].get('corroborating', [])
    ):
        raise ValueError('Planner runeword lacks its native source pin')
    runes = [recipe[f'Rune{i}'] for i in range(1, 7) if recipe.get(f'Rune{i}')]
    planner_runes = [planner_recipe[f'rune{i}'] for i in range(1, 7) if planner_recipe.get(f'rune{i}')]
    if (
        not runes
        or planner_runes != runes
        or item.get('socketedItems') != runes
        or type(item.get('sockets')) is not int
        or item['sockets'] != len(runes)
    ):
        raise ValueError('Planner runeword socket recipe is inconsistent')
    base = tables['weapons' if weapon else 'armor'].get(item.get('base'))
    if not base or base.get('gemsockets', 0) < len(runes):
        raise ValueError('Planner runeword requires a compatible native base')
    types = ancestors(base.get('type'), tables['types'])
    allowed = {recipe[f'itype{i}'] for i in range(1, 7) if recipe.get(f'itype{i}')}
    excluded = {recipe[f'etype{i}'] for i in range(1, 4) if recipe.get(f'etype{i}')}
    if not types.intersection(allowed) or types.intersection(excluded):
        raise ValueError('Planner runeword recipe is illegal on this base')
    for field, value in [('runeword', name), ('sockets', len(runes)), ('socket_contents', 'filled')]:
        if not requires_eq(role['must'], 'fact_eq', field, value):
            raise ValueError('Planner runeword must be mandatory in the reviewed rule')


def ancestors(code, definitions):
    result, pending = set(), [code]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        if current not in definitions:
            raise ValueError('Planner runeword base type is unknown')
        result.add(current)
        row = definitions[current]
        pending.extend(row[k] for k in ('Equiv1', 'Equiv2') if row.get(k))
    return result
