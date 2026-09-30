"""Native Insight mercenary and Hand of Justice source-example requirements."""

from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import WEAPON_SOURCES, ancestors
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


def weapon_component_role(evidence, role, build, read_json):
    kind = evidence.get('weapon_component')
    insight = kind == 'insight_mercenary'
    name, side = ('Insight', 'merc') if insight else ('Hand of Justice', 'player')
    if (
        kind not in ('insight_mercenary', 'hand_of_justice_player')
        or role.get('names') != [name]
        or role.get('side') != side
        or role.get('slot') != 'Weapon'
        or evidence.get('slot') != 'rarm'
        or evidence.get('coverage') != side + '_runeword_component'
        or evidence.get('stat_definitions', {}).get('path') != 'third-parties/d2data/json/itemstatcost.json'
    ):
        raise ValueError('Weapon component scope or native stat source invalid')
    pins = evidence.get('recipe_sources', {})
    if set(pins) != set(WEAPON_SOURCES) or any(pins[k].get('path') != v for k, v in WEAPON_SOURCES.items()):
        raise ValueError('Weapon component native recipe sources missing')
    tables = {k: read_json(pin) for k, pin in pins.items()}
    item = evidence.get('expected_item', {})
    base = tables['weapons'].get(item.get('base'), {})
    if not base.get('name') or not evidence.get('quote', '').startswith(name + ' ' + base['name']):
        raise ValueError('Weapon component primary base label differs from selected native item')
    aura = native_aura(item, name, tables, read_json(evidence['stat_definitions']))
    if not insight:
        expected = [
            ('ethereal', False),
            ('identified', True),
            ('runeword', name),
            ('sockets', 4),
            ('socket_contents', 'filled'),
            ('base_code', item['base']),
        ]
        if (
            'equipment_branches' in evidence
            or evidence.get('ethereal_scope') != 'nonethereal_only'
            or role.get('depends_on')
            or not all(requires_eq(role['must'], 'fact_eq', field, value) for field, value in expected)
            or not requires_eq(role['must'], 'context_eq', 'player_class', build['class'])
            or item.get('ethereal') is not False
        ):
            raise ValueError('Weapon component Hand of Justice item/class requirements changed')
        return role
    expected = [
        *[
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in [('runeword', name), ('sockets', 4), ('socket_contents', 'filled')]
        ],
        {'op': 'stat_at_least', 'key': aura['key'], 'value': aura['minimum']},
        {'op': 'fact_eq', 'field': 'base_code', 'value': item['base']},
    ]
    deps = role.get('depends_on', [])
    wearer = {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Holy Freeze'}
    if (
        role['must'] != {'all': expected}
        or role.get('types') != ['pole']
        or 'pole' not in ancestors(base.get('type'), tables['types'])
        or evidence.get('ethereal_scope') != 'known_status_example'
        or type(item.get('ethereal')) is not bool
        or len(deps) != 1
        or deps[0].get('required', True) is not True
        or not requires_eq(deps[0].get('when', {}), 'context_eq', 'mercenary_type', 'Act 2 Holy Freeze')
        or evidence.get('mercenary_type') != 'Act 2 Holy Freeze'
    ):
        raise ValueError('Weapon component Insight must preserve aura, base and required wearer')
    # Scope this source example, retaining the full original role in its review.
    # A preferred ethereal base is not made mandatory in the runtime rule.
    return {
        **role,
        'must': {
            'all': [
                role['must'],
                deps[0]['when'],
                wearer,
                {'op': 'fact_eq', 'field': 'ethereal', 'value': item['ethereal']},
            ]
        },
    }


def native_aura(item, name, tables, costs):
    aura_name = 'Meditation' if name == 'Insight' else 'Holy Fire'
    cost = costs.get('item_aura', {})
    recipe = tables['runes'][name]
    ids = [key for key, row in tables['planner']['skills'].items() if row.get('skill') == aura_name]
    slots = [i for i in range(1, 8) if recipe.get(f'T1Code{i}') == 'aura' and recipe.get(f'T1Param{i}') == aura_name]
    if cost.get('*ID') != 151 or cost.get('Stat') != 'item_aura' or len(ids) != 1 or len(slots) != 1:
        raise ValueError('Weapon component native aura definition changed')
    skill, slot = ids[0], slots[0]
    low, high = recipe[f'T1Min{slot}'], recipe[f'T1Max{slot}']
    value = item.get('stats', {}).get(f'item_aura#{skill}')
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Weapon component native aura missing or outside bounds')
    return {'key': f'151:{skill}', 'minimum': low}
