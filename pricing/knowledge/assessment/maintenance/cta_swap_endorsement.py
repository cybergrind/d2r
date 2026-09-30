"""Validate CTA native skills and Spirit on the same selected weapon swap."""

from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import (
    SOURCES,
    WEAPON_SOURCES,
    validate_runeword,
)
from pricing.knowledge.builds import decode_planner


BUILDS = 'pricing/data/wp-a-builds.json'
STATS = 'third-parties/d2data/json/itemstatcost.json'


def recipe_role(name, pin, *, slot, count):
    return {
        'names': [name],
        'slot': slot,
        'source': {'corroborating': [{**pin, 'locator': '/' + name}]},
        'must': {
            'all': [
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in [('runeword', name), ('sockets', count), ('socket_contents', 'filled')]
            ]
        },
    }


def cta_swap_role(evidence, role, build, read_json):
    if (
        evidence.get('prebuff_swap') != 'cta_spirit'
        or evidence.get('ethereal_scope') != 'unrestricted_reviewed_role'
        or evidence.get('coverage') != 'player_runeword_component'
        or role.get('names') != ['Call to Arms']
        or role.get('side') != 'player'
        or role.get('slot') != 'Weapon-Swap'
        or evidence.get('slot') != 'rarm2'
        or evidence.get('stat_definitions', {}).get('path') != STATS
    ):
        raise ValueError('CTA swap requires explicit native prebuff and unrestricted ethereal scope')
    pins = evidence.get('recipe_sources', {})
    if set(pins) != set(WEAPON_SOURCES) or any(pins[k].get('path') != v for k, v in WEAPON_SOURCES.items()):
        raise ValueError('CTA swap native recipe sources missing')
    tables = {k: read_json(pin) for k, pin in pins.items()}
    item = evidence.get('expected_item', {})
    base = tables['weapons'].get(item.get('base'), {})
    if not base.get('name') or ('ethereal' in item and type(item['ethereal']) is not bool):
        raise ValueError('CTA swap base or known ethereal flag invalid')
    predicates = [
        {'op': 'context_eq', 'field': 'player_class', 'value': build['class']},
        *[
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in [
                ('identified', True),
                ('base_code', item['base']),
                ('runeword', 'Call to Arms'),
                ('sockets', 5),
                ('socket_contents', 'filled'),
            ]
        ],
    ]
    predicates.extend(skill_requirements(item, tables, read_json(evidence['stat_definitions'])))
    dependencies = role.get('depends_on', [])
    if (
        role.get('must') != {'all': predicates}
        or len(dependencies) != 1
        or dependencies[0].get('required', True) is not True
        or dependencies[0].get('when')
        != {
            'op': 'context_contains',
            'field': 'player_swap_items',
            'value': 'Spirit',
        }
    ):
        raise ValueError('CTA swap must preserve native skills, item guards and required Spirit pairing')
    source = role['source']
    parts = source['locator'].strip('/').split('/')
    if (
        source['path'] != BUILDS
        or len(parts) != 3
        or parts[:2] != [role['build'], 'variants']
        or not parts[2].isdecimal()
        or str(int(parts[2])) != parts[2]
    ):
        raise ValueError('CTA swap requires its exact primary build variant')
    try:
        variant = read_json(source)[role['build']]['variants'][int(parts[2])]
        labels = variant['player']['Weapon-Swap']
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('CTA swap primary equipment source missing') from error
    if variant.get('name') != role['variant'] or not any(
        label.startswith('Call to Arms ' + base['name']) for label in labels if isinstance(label, str)
    ):
        raise ValueError('CTA swap primary base recommendation changed')
    validate_spirit(evidence, variant, read_json)
    return {
        **role,
        'source': {
            **source,
            'corroborating': [
                *source.get('corroborating', []),
                {**pins['runes'], 'locator': '/Call to Arms'},
            ],
        },
    }


def skill_requirements(item, tables, costs):
    stat = costs.get('item_nonclassskill', {})
    if stat.get('*ID') != 97 or stat.get('Stat') != 'item_nonclassskill':
        raise ValueError('CTA swap native oskill definition changed')
    recipe = tables['runes']['Call to Arms']
    result = []
    for name in ('Battle Orders', 'Battle Command'):
        ids = [key for key, skill in tables['planner']['skills'].items() if skill.get('skill') == name]
        slots = [i for i in range(1, 8) if recipe.get(f'T1Code{i}') == 'oskill' and recipe.get(f'T1Param{i}') == name]
        if len(ids) != 1 or len(slots) != 1:
            raise ValueError('CTA swap native skill identity ambiguous')
        skill_id, slot = ids[0], slots[0]
        low, high = recipe[f'T1Min{slot}'], recipe[f'T1Max{slot}']
        value = item.get('stats', {}).get(f'item_nonclassskill#{skill_id}')
        if type(value) is not int or not low <= value <= high:
            raise ValueError('CTA swap native skill roll missing or outside bounds')
        result.append({'op': 'stat_at_least', 'key': f'97:{skill_id}', 'value': low, 'absent_is_zero': True})
    return result


def validate_spirit(evidence, variant, read_json):
    companion = evidence.get('companion', {})
    pins = companion.get('recipe_sources', {})
    if set(pins) != set(SOURCES) or any(pins[k].get('path') != v for k, v in SOURCES.items()):
        raise ValueError('CTA swap requires pinned Spirit companion evidence')
    planner = decode_planner(read_json(evidence['planner']))
    index = evidence.get('profile_index')
    if type(index) is not int or not 0 <= index < len(planner['profiles']):
        raise ValueError('CTA swap selected profile invalid')
    profile = planner['profiles'][index]
    item_id = str(profile.get('items', {}).get('larm2'))
    item = planner['items'].get(item_id)
    if (
        not item
        or item.get('quality') != 7
        or companion.get('item_id') != item_id
        or companion.get('locator') != f'/profiles/{index}/items/larm2'
        or companion.get('item') != item
    ):
        raise ValueError('CTA swap Spirit must be the actual selected offhand swap')
    base = read_json(pins['armor']).get(item.get('base'), {})
    if not base.get('name') or not any(
        label.startswith('Spirit ' + base['name'])
        for key in ('Off-Hand-Swap', 'Off-Hand Swap')
        for label in variant['player'].get(key, [])
        if isinstance(label, str)
    ):
        raise ValueError('CTA swap primary source does not establish its Spirit companion')
    role = recipe_role('Spirit', pins['runes'], slot='Off-Hand-Swap', count=4)
    validate_runeword({'recipe_sources': pins}, role, item, read_json)
