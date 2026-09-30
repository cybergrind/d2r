"""Native minima and rune proof for selected mercenary helms and Warlock grimoires."""

from pricing.knowledge.assessment.maintenance.planner_equipment_quote import equipment_quote_matches
from pricing.knowledge.definitions import scalar_ranges


SOURCES = {
    'metadata': 'inventory_tracking/items/data/item_metadata.json',
    'uniques': 'third-parties/d2data/json/uniqueitems.json',
    'properties': 'third-parties/d2data/json/properties.json',
    'stats': 'third-parties/d2data/json/itemstatcost.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'gems': 'third-parties/d2data/json/gems.json',
    'game': 'pricing/raw/mr/planners/game-data.json',
}
CONFIGS = {
    'hammer-mf-stealskull-merc': ('203', ('60:0', '80:0', '93:0'), 'Paladin', 'Act 2 Holy Freeze', 'Ist Rune'),
    'lightning-fury-ubers-gaze-merc': ('208', ('60:0', '36:0'), 'Amazon', 'Act 5 Frenzy', 'Um Rune'),
    'fire-warlock-standard-ars-diabolos': ('408', ('188:58', '105:0', '329:0', '107:401'), 'Warlock', None, 'Um Rune'),
    'fire-warlock-mf-ars-diabolos': ('408', ('188:58', '105:0', '329:0', '107:401'), 'Warlock', None, 'Ist Rune'),
}


def named_socket_role(evidence, role, build, read_json):
    config = CONFIGS.get(role.get('id'))
    pins = evidence.get('native_sources', {})
    if (
        config is None
        or evidence.get('named_socket') != 'native_unique'
        or set(pins) != set(SOURCES)
        or any(pins[k].get('path') != path for k, path in SOURCES.items())
    ):
        raise ValueError('Named socket scope or native sources invalid')
    key, required_keys, player_class, mercenary, rune_name = config
    side, slot, native_slot = ('merc', 'Helmet', 'head') if mercenary else ('player', 'Off-Hand', 'larm')
    if (
        role.get('side') != side
        or role.get('slot') != slot
        or evidence.get('slot') != native_slot
        or role.get('qualities') != ['unique']
        or build.get('class') != player_class
        or evidence.get('coverage') != side + '_rune_socket_component'
        or role.get('required_rune') != rune_name
    ):
        raise ValueError('Named socket item or wearer scope changed')
    tables = {k: read_json(pin) for k, pin in pins.items()}
    item = evidence.get('expected_item', {})
    native = tables['uniques'].get(key)
    identity = tables['metadata']['identities']['unique'].get(key)
    if (
        not native
        or not identity
        or identity.get('game_definition') != native
        or role.get('names') != [identity.get('name')]
        or item.get('quality') != 6
        or item.get('unique') != 'unique' + key
        or item.get('base') != native.get('code')
        or ('ethereal' in item and type(item['ethereal']) is not bool)
        or (not mercenary and item.get('ethereal') is True)
        or (key == '203' and item.get('ethereal') is not True)
    ):
        raise ValueError('Named socket native identity, base or ethereal scope differs')
    stat_ids = {name: row['*ID'] for name, row in tables['stats'].items() if '*ID' in row}
    skill_ids = {row['name']: int(key) for key, row in tables['metadata']['skills'].items()}
    ranges = scalar_ranges(native, tables['properties'], stat_ids, skill_ids=skill_ids)
    predicates = (
        []
        if mercenary
        else [
            {'op': 'context_eq', 'field': 'player_class', 'value': player_class},
            {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        ]
    )
    for stat_key in required_keys:
        sid, layer = map(int, stat_key.split(':'))
        spec = ranges.get(str(sid) if layer == 0 else stat_key)
        if not spec:
            raise ValueError('Named socket required native stat range unresolved')
        names = [name for name, value in stat_ids.items() if value == sid]
        if len(names) != 1:
            raise ValueError('Named socket native stat identity ambiguous')
        # Planner tabs use table indices; runtime layers pack class*8 + tree.
        parameter = (layer // 8) * 3 + layer % 8 if sid == 188 else layer
        observed_key = names[0] + (f'#{parameter}' if layer else '')
        value = item.get('stats', {}).get(observed_key)
        if type(value) is not int or not spec['min'] <= value <= spec['max']:
            raise ValueError('Named socket required observed stat outside native bounds')
        predicates.append({'op': 'stat_at_least', 'key': stat_key, 'value': spec['min'], 'absent_is_zero': True})
    if role.get('must') != {'all': predicates}:
        raise ValueError('Named socket native minimum guards changed')
    extra = []
    deps = role.get('depends_on', [])
    if mercenary:
        from pricing.knowledge.assessment.maintenance.armor_planner_links import validate_armor_mercenary

        predicate = {'op': 'context_eq', 'field': 'mercenary_type', 'value': mercenary}
        if len(deps) != 1 or deps[0].get('when') != predicate or deps[0].get('required', True) is not True:
            raise ValueError('Named socket required mercenary dependency changed')
        validate_armor_mercenary(
            {'mercenary_type': mercenary, 'mercenary_id': evidence.get('mercenary_id')}, tables['game']
        )
        extra.append(predicate)
    elif deps:
        raise ValueError('Named socket player dependencies changed')
    base = tables['armor'].get(item['base'], {})
    codes = item.get('socketedItems')
    if (
        base.get('gemsockets', 0) < 1
        or type(item.get('sockets')) is not int
        or item['sockets'] != 1
        or not isinstance(codes, list)
        or len(codes) != 1
        or not isinstance(codes[0], str)
        or tables['gems'].get(codes[0], {}).get('name') != rune_name
    ):
        raise ValueError('Named socket required rune payload or capacity differs')
    equipment_quote_matches(evidence, role, read_json, allow_unquoted=True)
    if rune_name not in evidence['quote'] or identity['name'] not in evidence['quote']:
        raise ValueError('Named socket primary quote must identify item and rune')
    if key == '203':
        extra.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
    extra.extend(
        {'op': 'fact_eq', 'field': field, 'value': value}
        for field, value in [
            ('base_code', item['base']),
            ('sockets', 1),
            ('socket_contents', 'filled'),
        ]
    )
    extra.append({'op': 'socket_runes_equal', 'value': [rune_name]})
    return {
        **role,
        'must': {'all': [role['must'], *extra]},
        'source': {
            **role['source'],
            'quotes': [*role['source'].get('quotes', []), evidence['quote']],
            'corroborating': [
                *role['source'].get('corroborating', []),
                {**pins['uniques'], 'locator': '/' + key},
                {**pins['gems'], 'locator': '/' + codes[0]},
            ],
        },
    }
