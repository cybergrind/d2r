"""Selected Sazabi mercenary set and rune proof, independent of active prebuffs."""

import hashlib

from pricing.knowledge.assessment.maintenance.planner_set_endorsement import validate_set_identity
from pricing.knowledge.builds import decode_planner


SOURCES = {
    'profiles': 'pricing/data/appraisal-build-profiles.json',
    'game': 'pricing/raw/mr/planners/game-data.json',
    'sets': 'third-parties/d2data/json/setitems.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'weapons': 'third-parties/d2data/json/weapons.json',
    'gems': 'third-parties/d2data/json/gems.json',
}
SLOTS = {'head': ('helm', 'Helmet'), 'tors': ('armor', 'Body Armor'), 'rarm': ('sword', 'Weapon')}
MECHANICS = 'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp'
SET = "Sazabi's Grand Tribute"


def sazabi_loadout_role(evidence, role, build, read_json, root):
    pins = evidence.get('set_sources', {})
    slot = evidence.get('slot')
    if (
        evidence.get('set_loadout') != 'sazabi_frenzy'
        or evidence.get('coverage') != 'merc_set_component'
        or evidence.get('ethereal_scope') != 'legal_nonethereal_set'
        or slot not in SLOTS
        or role.get('id') != 'echoing-ubers-sazabi-' + SLOTS[slot][0]
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or build.get('class') != 'Warlock'
        or set(pins) != set(SOURCES)
        or any(pins[k].get('path') != path for k, path in SOURCES.items())
    ):
        raise ValueError('Sazabi mercenary source scope invalid')
    validate_set_ethereal_scope(evidence, root)
    tables = {k: read_json(pin) for k, pin in pins.items()}
    roles = {r['id']: r for r in tables['profiles']['profiles']}
    if roles.get(role['id']) != role:
        raise ValueError('Sazabi reviewed role changed')
    planner = decode_planner(read_json(evidence['planner']))
    index = evidence.get('profile_index')
    if type(index) is not int or not 0 <= index < len(planner['profiles']):
        raise ValueError('Sazabi selected profile invalid')
    profile = planner['profiles'][index]
    if profile.get('name') != role['variant'] or profile.get('class') != 'war':
        raise ValueError('Sazabi selected variant or wearer differs')
    from pricing.knowledge.assessment.maintenance.armor_planner_links import validate_armor_mercenary

    validate_armor_mercenary(
        {'mercenary_type': 'Act 5 Frenzy', 'mercenary_id': str(profile.get('merc'))}, tables['game']
    )
    members = {name for name, row in tables['sets'].items() if row.get('set') == SET and row.get('spawnable') == 1}
    observed = set()
    items = {}
    for native_slot, (suffix, label) in SLOTS.items():
        component = roles.get('echoing-ubers-sazabi-' + suffix, {})
        name = component.get('names', [None])[0]
        item = planner['items'].get(str(profile.get('mercItems', {}).get(native_slot)), {})
        validate_component(component, item, native_slot, label, members, tables, pins, read_json)
        if name in observed:
            raise ValueError('Sazabi duplicate set member')
        observed.add(name)
        items[native_slot] = item
    if observed != members or len(members) != 3:
        raise ValueError('Sazabi full set membership changed')
    item = items[slot]
    codes = item['socketedItems']
    return {
        **role,
        'must': {
            'all': [
                role['must'],
                *[
                    {'op': 'fact_eq', 'field': field, 'value': value}
                    for field, value in [('base_code', item['base']), ('sockets', 1), ('socket_contents', 'filled')]
                ],
                {'op': 'socket_runes_equal', 'value': [role['required_rune']]},
            ]
        },
        'source': {
            **role['source'],
            'corroborating': [
                *role['source'].get('corroborating', []),
                {**pins['sets'], 'locator': '/' + role['names'][0]},
                *[{**pins['gems'], 'locator': '/' + code} for code in codes],
            ],
        },
    }


def validate_component(role, item, slot, label, members, tables, pins, read_json):
    name = role.get('names', [None])[0]
    expected = {
        'all': [
            {'op': 'fact_eq', 'field': 'name', 'value': name},
            {'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'},
            {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 5 Frenzy'},
            {'op': 'fact_eq', 'field': 'identified', 'value': True},
            {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        ]
    }
    if (
        name not in members
        or role.get('side') != 'merc'
        or role.get('slot') != label
        or role.get('qualities') != ['set']
        or role.get('must') != expected
        or role.get('mercenary_type') != 'Act 5 Frenzy'
        or set(role.get('companions', [])) != members - {name}
        or role.get('review_status') != 'reviewed_setup'
        or item.get('quality') != 5
        or ('ethereal' in item and item['ethereal'] is not False)
    ):
        raise ValueError('Sazabi piece or required companions changed')
    validate_set_identity({'set_definitions': pins['sets'], 'planner_definitions': pins['game']}, role, item, read_json)
    base = tables['weapons' if slot == 'rarm' else 'armor'].get(item.get('base'), {})
    codes = item.get('socketedItems')
    if (
        not base
        or base.get('gemsockets', 0) < 1
        or type(item.get('sockets')) is not int
        or item['sockets'] != 1
        or not isinstance(codes, list)
        or len(codes) != 1
        or not isinstance(codes[0], str)
    ):
        raise ValueError('Sazabi socket capacity or payload invalid')
    rune = tables['gems'].get(codes[0], {})
    channel = 'weapon' if slot == 'rarm' else 'helm'
    effect, value = {'head': ('nofreeze', 1), 'tors': ('red-dmg%', 8), 'rarm': ('crush', 20)}[slot]
    if (
        rune.get('code') != codes[0]
        or rune.get('name') != role.get('required_rune')
        or rune.get(channel + 'Mod1Code') != effect
        or rune.get(channel + 'Mod1Min') != value
        or rune.get(channel + 'Mod1Max') != value
    ):
        raise ValueError('Sazabi required native rune or slot effect changed')


def validate_set_ethereal_scope(evidence, root):
    pin = evidence.get('ethereal_mechanics', {})
    if pin.get('path') != MECHANICS:
        raise ValueError('Sazabi legal set scope requires pinned ethereal mechanics')
    raw = (root / MECHANICS).read_bytes()
    # This is a reviewed legacy implementation reference, not an observed flag.
    # Pin its quality exclusion and reject explicitly contradictory planner data.
    guard = 'if (nItemQuality == ITEMQUAL_INFERIOR || nItemQuality == ITEMQUAL_SET || ITEMS_IsQuestItem(pItem))'
    function = raw.decode().split('void __fastcall ITEMS_MakeEthereal(', 1)[-1].split('//D2Game.', 1)[0]
    if (
        hashlib.sha256(raw).hexdigest() != pin.get('sha256')
        or guard + '\n    {\n        return;\n    }' not in function
    ):
        raise ValueError('Sazabi set ethereal exclusion reference changed')
