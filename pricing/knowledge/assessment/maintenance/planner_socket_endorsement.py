"""Validate rune-only sockets against pinned native definitions and runtime guards."""

from pricing.knowledge.assessment.maintenance.source_matching import requires


def validate_rune_socket(evidence, role, item, read_json):
    preparation = evidence.get('coverage') == 'player_rune_socket_preparation'
    pin = evidence.get('rune_definitions', {})
    if pin.get('path') != 'third-parties/d2data/json/gems.json':
        raise ValueError('Planner rune definitions are required')
    definitions = read_json(pin)
    codes = item.get('socketedItems')
    count = item.get('sockets')
    if type(count) is not int or count < 1 or not isinstance(codes, list) or len(codes) != count:
        raise ValueError('Planner rune socket count is inconsistent')
    names = []
    for code in codes:
        if not isinstance(code, str) or code not in definitions:
            raise ValueError('Planner rune socket contains unsupported payload')
        definition = definitions[code]
        name = definition.get('name', '')
        if not name.endswith(' Rune') or definition.get('code') != code:
            raise ValueError('Planner socket is not a native rune')
        if not preparation and not any(
            ref.get('path') == pin['path']
            and ref.get('sha256') == pin.get('sha256')
            and ref.get('locator') == '/' + code
            for ref in role['source'].get('corroborating', [])
        ):
            raise ValueError('Planner rune lacks its native source pin')
        names.append(name)
    if preparation:
        note = evidence.get('preparation_note')
        predicate = {'op': 'socket_runes_equal', 'value': names}
        if (
            not isinstance(note, str)
            or not note.strip()
            or not any(requires(dependency['when'], predicate) for dependency in role.get('depends_on', []))
        ):
            raise ValueError('Planner rune preparation must require the actual linked runes')
        return
    expected = (
        {'op': 'fact_eq', 'field': 'sockets', 'value': count},
        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
        {'op': 'socket_runes_equal', 'value': names},
    )
    if not all(requires(role['must'], predicate) for predicate in expected):
        raise ValueError('Planner rune socket is not mandatory in the reviewed rule')
