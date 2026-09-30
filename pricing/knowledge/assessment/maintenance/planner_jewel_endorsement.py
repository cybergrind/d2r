"""Source proof for one linked rare recovery/resistance jewel, not parent totals."""

from pricing.knowledge.assessment.maintenance.planner_jewel_affixes import reviewed_bounds
from pricing.knowledge.assessment.maintenance.source_matching import requires


TABLE_PATHS = {
    'mp': 'third-parties/d2data/json/magicprefix.json',
    'ms': 'third-parties/d2data/json/magicsuffix.json',
}


def validate_jewel_socket(evidence, role, item, planner, read_json):
    pin = evidence.get('jewel', {})
    item_id = pin.get('item_id')
    if (
        not isinstance(item_id, str)
        or not item_id.isdecimal()
        or type(item.get('sockets')) is not int
        or item.get('sockets') != 1
        or item.get('socketedItems') != [int(item_id)]
    ):
        raise ValueError('Planner jewel is not the actual single socket child')
    jewel = planner['items'].get(item_id)
    if not jewel or jewel != pin.get('expected_item'):
        raise ValueError('Planner jewel snapshot changed')
    refs = role['source'].get('corroborating', [])
    table_pins = pin.get('affix_definitions', {})
    if set(table_pins) != set(TABLE_PATHS) or any(table_pins[k].get('path') != path for k, path in TABLE_PATHS.items()):
        raise ValueError('Planner jewel needs pinned native affix tables')
    bounds = reviewed_bounds(jewel, {key: read_json(value) for key, value in table_pins.items()})
    for mod in jewel['mods']:
        native = table_pins[mod[:2]]
        if not any(
            ref.get('path') == native['path']
            and ref.get('sha256') == native.get('sha256')
            and ref.get('locator') == '/' + mod[2:]
            for ref in refs
        ):
            raise ValueError('Planner jewel affix lacks its reviewed native pin')
    stat_pin = pin.get('stat_definitions', {})
    if stat_pin.get('path') != 'third-parties/d2data/json/itemstatcost.json':
        raise ValueError('Planner jewel native stat definitions are required')
    definitions = read_json(stat_pin)
    stats = {}
    for name, (minimum, _) in bounds.items():
        row = definitions.get(name, {})
        if type(row.get('*ID')) is not int:
            raise ValueError('Unknown planner jewel stat identity')
        stats[f'{row["*ID"]}:0'] = minimum
    predicates = (
        {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
        {'op': 'socket_jewel_matches', 'count': 1, 'stats': stats},
    )
    if not all(requires(role['must'], predicate) for predicate in predicates):
        raise ValueError('Planner jewel properties are not mandatory in the reviewed rule')
