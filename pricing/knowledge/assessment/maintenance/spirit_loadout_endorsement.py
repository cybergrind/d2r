"""Validate active Hammerdin Spirit examples without weakening loadout requirements."""

from pricing.knowledge.assessment.maintenance.planner_fcr import SOURCE_PATHS, active_fcr_evidence, native_recipe
from pricing.knowledge.builds import decode_planner


COMPANIONS = {
    'Standard': ('Sling', "Hellwarden's Will"),
    'Magic Find': ('Void', 'Sling', 'Arachnid Mesh'),
}


def spirit_loadout_role(evidence, role, build, read_json):
    pins = evidence.get('fcr_sources', {})
    if (
        evidence.get('spirit_loadout') != 'hammer_active'
        or evidence.get('coverage') != 'player_runeword_component'
        or evidence.get('ethereal_scope') != 'unrestricted_reviewed_role'
        or evidence.get('slot') != 'larm'
        or role.get('build') != 'blessed-hammer-paladin'
        or role.get('variant') not in COMPANIONS
        or role.get('side') != 'player'
        or role.get('slot') != 'Off-Hand'
        or role.get('names') != ['Spirit']
        or build.get('class') != 'Paladin'
        or set(pins) != set(SOURCE_PATHS)
        or any(pins[k].get('path') != path for k, path in SOURCE_PATHS.items())
    ):
        raise ValueError('Spirit active loadout scope or native sources invalid')
    tables = {k: read_json(pin) for k, pin in pins.items()}
    planner = decode_planner(read_json(evidence['planner']))
    index = evidence.get('profile_index')
    if type(index) is not int or not 0 <= index < len(planner['profiles']):
        raise ValueError('Spirit selected profile invalid')
    profile = planner['profiles'][index]
    item = planner['items'].get(str(profile.get('items', {}).get('larm')), {})
    if (
        profile.get('name') != role['variant']
        or profile.get('class') != 'pal'
        or item.get('quality') != 7
        or ('ethereal' in item and type(item['ethereal']) is not bool)
        or native_recipe(item, tables)[0] != 'Spirit'
    ):
        raise ValueError('Spirit selected active item or class differs')
    predicates = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        *[
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in [
                ('identified', True),
                ('base_code', item['base']),
                ('runeword', 'Spirit'),
                ('sockets', 4),
                ('socket_contents', 'filled'),
            ]
        ],
    ]
    dependencies = role.get('depends_on', [])
    expected = [
        {'op': 'context_at_least', 'field': 'player_total_fcr', 'value': 125},
        *[{'op': 'context_contains', 'field': 'player_items', 'value': name} for name in COMPANIONS[role['variant']]],
    ]
    if (
        role.get('must') != {'all': predicates}
        or [d.get('when') for d in dependencies] != expected
        or any(d.get('required', True) is not True for d in dependencies)
    ):
        raise ValueError('Spirit must preserve item guards, 125 FCR and required named companions')
    result = active_fcr_evidence(profile, planner['items'], tables)
    names = {r['name'] for r in result['contributors']}
    if result['minimum_fcr'] < 125 or not set(COMPANIONS[role['variant']]) <= names:
        raise ValueError('Spirit selected loadout lacks 125 FCR or required active companions')
    # Source-example evidence only; do not add a perfect Spirit roll, resistance
    # minimum or inferred nonethereal flag to the runtime role.
    return {
        **role,
        'source': {
            **role['source'],
            'corroborating': [
                *role['source'].get('corroborating', []),
                {**pins['runes'], 'locator': '/Spirit'},
            ],
        },
    }
