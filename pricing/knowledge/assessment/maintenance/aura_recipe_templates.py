"""Reviewed aura recipes with equipment-slot and repair dependencies."""

from pricing.knowledge.assessment.adapters.capture import bases_by_code
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Mosaic': {'dragon-talon-assassin': ('Assassin', ('Off-Hand',))},
    'Coven': {'fire-warlock-guide': ('Warlock', ('Helmets',))},
    'Dream': {'dream-paladin': ('Paladin', ('Helmets', 'Off-Hand'))},
    'Dragon': {'dream-paladin': ('Paladin', ('Body Armor',))},
    'Phoenix': {'fire-warlock-guide': ('Warlock', ('Off-Hand',)), 'fissure-druid': ('Druid', ('Weapon', 'Off-Hand'))},
    'Exile': {'smite-paladin': ('Paladin', ('Off-Hand',))},
}


def member_types(name, slot):
    if name == 'Mosaic':
        return ['h2h', 'h2h2']
    if name == 'Coven':
        return ['circ']
    if name == 'Dream':
        return ['helm', 'circ'] if slot == 'Helmets' else ['shie', 'ashd']
    if name == 'Dragon':
        return ['tors']
    if name == 'Exile':
        return ['ashd']
    return (
        ['axe', 'hamm', 'mace', 'pole', 'scep', 'spea', 'staf', 'swor', 'bow', 'xbow'] if slot == 'Weapon' else ['shie']
    )


def recipe_condition(name, types):
    return {
        'all': [
            *[
                {'op': 'fact_eq', 'field': key, 'value': value}
                for key, value in (
                    ('identified', True),
                    ('runeword', name),
                    ('sockets', len(catalog().runewords[name]['runes'])),
                    ('socket_contents', 'filled'),
                )
            ],
            legal_base_condition(name, types),
        ]
    }


def priorities(name, slot):
    if name == 'Mosaic':
        return ('188:50', '200:0', '329:0', '330:0', '331:0')
    if name == 'Coven':
        return ('127:0', '105:0', '16:0', '80:0', '86:0', '39:0', '3:0')
    if name == 'Dream':
        return (
            '151:118',
            '99:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '31:0',
            '16:0',
            '3:0',
            '217:0',
            '80:0',
            '76:0' if slot == 'Helmets' else '7:0',
        )
    if name == 'Dragon':
        return ('151:102', '31:0', '32:0', '220:0', '0:0', '1:0', '2:0', '3:0', '77:0', '42:0', '34:0')
    if name == 'Phoenix':
        return ('333:0', '151:124', '143:0', '32:0', *(('40:0', '42:0', '7:0') if slot == 'Off-Hand' else ()))
    return (
        '151:104',
        '188:25',
        '102:0',
        '16:0',
        '252:0',
        '198:5253',
        '40:0',
        '44:0',
        '80:0',
        '74:0',
        '39:0',
        '41:0',
        '43:0',
        '45:0',
    )


def expand_aura_recipe(row):
    name, build, slot = row['item'], row['build'], row['slot']
    if name not in MEMBERS or build not in MEMBERS[name]:
        raise ValueError('Unknown aura recipe use')
    klass, slots = MEMBERS[name][build]
    if row['class'] != klass or slot not in slots or row['side'] != 'player':
        raise ValueError('Invalid aura recipe wearer or slot')
    types = member_types(name, slot)
    noneth = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = (
        noneth
        if name != 'Exile'
        else {
            'any': [
                noneth,
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                        {'op': 'stat_at_least', 'key': '252:0', 'value': 1, 'absent_is_zero': True},
                    ]
                },
            ]
        }
    )
    must = [{'op': 'context_eq', 'field': 'player_class', 'value': klass}, recipe_condition(name, types)]
    if name != 'Phoenix' or slot != 'Weapon':
        must.append(durability)
    dependencies = []
    if name == 'Mosaic':
        other = recipe_condition('Mosaic', ['h2h', 'h2h2'])
        dependencies = [
            {
                'label': 'Equip the other Mosaic claw for the dual-claw charged-finisher setup.',
                'when': {
                    'op': 'equipped_item_matches',
                    'field': 'player_equipment',
                    'slot': 'weapon',
                    'when': {'all': [other, noneth]},
                },
            }
        ]
        role = 'Dual-Mosaic Martial Arts charged-finisher off-hand alternative'
        conditions = [
            'One Mosaic has a 50% chance not to consume charges; the paired setup needs another equipped '
            'Mosaic. Build the intended Martial Arts charges before finishing. Elemental skill damage helps '
            'the corresponding charge skills, not plain physical kicks. Weapon ED does not increase kick '
            'damage; off-hand IAS alone does not establish the kick breakpoint. Native staffmods remain '
            'separate.'
        ]
    elif name == 'Coven':
        code = next(code for code, b in bases_by_code().items() if b['name'] == 'Diadem')
        must.append({'op': 'fact_eq', 'field': 'base_code', 'value': code})
        role = 'Fire caster Coven Diadem alternative'
        conditions = [
            'The source specifies a Diadem. Added Ist magic find is separate from the recipe roll. Sigil '
            'Lethargy when struck is not assumed active; check the actual casting breakpoint.'
        ]
    elif name == 'Dream':
        other = 'off_hand' if slot == 'Helmets' else 'head'
        other_types = member_types(name, 'Off-Hand' if slot == 'Helmets' else 'Helmets')
        dependencies = [
            {
                'label': 'Equip the other Dream in the complementary slot for the dual-Dream setup.',
                'when': {
                    'op': 'equipped_item_matches',
                    'field': 'player_equipment',
                    'slot': other,
                    'when': {'all': [recipe_condition(name, other_types), noneth]},
                },
            }
        ]
        role = 'Dual-Dream Holy Shock equipment component'
        conditions = [
            'This piece supplies level 15 Holy Shock. The paired setup needs an equipped Dream in the other '
            'slot; a name in inventory is insufficient. Aura damage still depends on the skill/synergy setup '
            'and target resistance. Confuse when struck is not guaranteed.'
        ]
    elif name == 'Dragon':
        role = 'Dream Paladin supplemental Holy Fire armor alternative'
        conditions = [
            'This armor adds Holy Fire, not another Holy Shock aura. Its damage depends on the appropriate '
            'synergy setup and target resistance. Hydra and Venom procs are not assumed active; this role '
            'does not imply a second Dragon or Hand of Justice.'
        ]
    elif name == 'Phoenix':
        role = 'Fire caster resistance reduction and Redemption alternative'
        conditions = [
            'Fire resistance reduction applies to the active wielder. Redemption needs usable corpses, so '
            'sustain is not guaranteed against isolated bosses. Enhanced Damage and attack procs do not '
            'multiply fire spell damage. Weapon and shield rune effects differ; ethereal is accepted only '
            'for a casting weapon.'
        ]
    else:
        role = 'Smite self-repairing Defiance and Life Tap shield alternative'
        conditions = [
            'Offensive Auras skill levels support the appropriate aura, not Combat Skills. Life Tap requires '
            'its on-striking proc; do not assume it is already active. Ethereal use requires observed self- '
            'repair. Base resistances, defense, block setup and repair pace remain relevant.'
        ]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': role,
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': types,
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'depends_on': dependencies,
        'important_stats': list(priorities(name, slot)),
        'conditions': conditions,
    }
