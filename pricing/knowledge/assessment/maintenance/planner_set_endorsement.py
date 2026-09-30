"""Validate individual planner set pieces without inferring set completion."""


def validate_set_component(evidence, role, item, read_json):
    validate_set_identity(evidence, role, item, read_json)
    note = evidence.get('component_note')
    if not isinstance(note, str) or not note.strip():
        raise ValueError('Planner set component must retain its standalone review scope')
    if item.get('sockets') != 0 or item.get('socketedItems'):
        raise ValueError('Planner set component needs a separate socket-payload review')


def validate_set_identity(evidence, role, item, read_json):
    native_pin = evidence.get('set_definitions', {})
    planner_pin = evidence.get('planner_definitions', {})
    if (
        native_pin.get('path') != 'third-parties/d2data/json/setitems.json'
        or planner_pin.get('path') != 'pricing/raw/mr/planners/game-data.json'
    ):
        raise ValueError('Planner set component requires pinned native and planner definitions')
    native = read_json(native_pin)
    planner = read_json(planner_pin)['setItems']
    names = role.get('names', [])
    definition = native.get(names[0]) if len(names) == 1 else None
    planned = planner.get(item.get('unique'))
    if (
        not definition
        or not planned
        or item.get('unique') != f'set{definition["*ID"]:03d}'
        or planned.get('index') != names[0]
        or planned.get('item') != definition.get('item')
        or item.get('base') != definition.get('item')
        or planned.get('set') != definition.get('set')
    ):
        raise ValueError('Planner set component identity or base differs from native definition')
