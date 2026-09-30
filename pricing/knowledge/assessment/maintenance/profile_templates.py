"""Expand explicitly reviewed family templates into the ordinary runtime schema."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.aura_recipe_templates import expand_aura_recipe
from pricing.knowledge.assessment.maintenance.caster_core_templates import expand_caster_core
from pricing.knowledge.assessment.maintenance.charge_utility_templates import expand_charge_utility
from pricing.knowledge.assessment.maintenance.combat_weapon_templates import expand_combat_weapon
from pricing.knowledge.assessment.maintenance.core_caster_word_templates import expand_core_caster_word
from pricing.knowledge.assessment.maintenance.delivery_weapon_templates import expand_delivery_weapon
from pricing.knowledge.assessment.maintenance.footwear_templates import expand_footwear
from pricing.knowledge.assessment.maintenance.merc_survival_templates import expand_merc_survival
from pricing.knowledge.assessment.maintenance.merc_sword_templates import expand_merc_sword
from pricing.knowledge.assessment.maintenance.merc_weapon_templates import expand_merc_weapon, expand_named_merc_weapon
from pricing.knowledge.assessment.maintenance.named_jewel_templates import expand_named_jewel
from pricing.knowledge.assessment.maintenance.named_shield_templates import expand_named_shield
from pricing.knowledge.assessment.maintenance.named_utility_templates import expand_named_utility
from pricing.knowledge.assessment.maintenance.progression_equipment_templates import expand_progression_equipment
from pricing.knowledge.assessment.maintenance.qualified_equipment_templates import expand_qualified_equipment
from pricing.knowledge.assessment.maintenance.renewed_sunder_templates import expand_renewed_sunder
from pricing.knowledge.assessment.maintenance.resistance_armor_templates import expand_resistance_armor
from pricing.knowledge.assessment.maintenance.source_recipe_templates import expand_source_recipe
from pricing.knowledge.assessment.maintenance.sunder_templates import expand_sunder_charm
from pricing.knowledge.assessment.maintenance.tal_caster_templates import expand_tal_caster
from pricing.knowledge.assessment.maintenance.throwing_templates import expand_named_throwing
from pricing.knowledge.definition_store import catalog


def expand_profile(row):
    template = row.get('template')
    if template is None:
        return row
    try:
        expand = EXPANDERS[template]
    except KeyError as error:
        raise ValueError(f'Unknown reviewed profile template: {template}') from error
    return expand(row)


def expand_unique_inventory_charm(row):
    name, class_name = row['item'], row['class']
    if name not in ('Annihilus', 'Hellfire Torch') or class_name not in CLASS_NAMES or row['side'] != 'player':
        raise ValueError('Invalid unique inventory charm template membership')
    definition = catalog().named['unique', name]
    class_id = CLASS_NAMES.index(class_name)
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': class_name},
        *[
            {'op': 'fact_eq', 'field': key, 'value': value}
            for key, value in (
                ('identified', True),
                ('base_code', definition['base_codes'][0]),
                ('ethereal', False),
                ('sockets', 0),
                ('socket_contents', 'empty'),
            )
        ],
    ]
    important = ['0:0', '1:0', '2:0', '3:0', '39:0', '41:0', '43:0', '45:0']
    if name == 'Hellfire Torch':
        skill = f'83:{class_id}'
        must.extend(
            [
                {'op': 'stat_at_least', 'key': skill, 'value': 3, 'absent_is_zero': True},
                {'not': {'op': 'stat_at_least', 'key': skill, 'value': 4}},
                *[
                    {'not': {'op': 'stat_at_least', 'key': f'83:{other}', 'value': 1, 'absent_is_zero': True}}
                    for other in range(len(CLASS_NAMES))
                    if other != class_id
                ],
            ]
        )
        important.insert(0, skill)
    else:
        important = ['127:0', *important, '85:0']
    level = definition['game_definition']['lvl req']
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': 'Inventory skill, attributes and resistance support',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {'all': must},
        'important_stats': important,
        'conditions': [
            f'Keep in active inventory and meet level {level}; owning a second copy does not stack its bonuses.',
            *row.get('conditions', []),
        ],
    }


EXPANDERS = {
    'core_caster_word': expand_core_caster_word,
    'tal_caster_gear': expand_tal_caster,
    'caster_core_gear': expand_caster_core,
    'named_socket_jewel': expand_named_jewel,
    'renewed_sunder': expand_renewed_sunder,
    'merc_sword_tail': expand_merc_sword,
    'named_shield_tail': expand_named_shield,
    'source_recipe': expand_source_recipe,
    'resistance_rune_armor': expand_resistance_armor,
    'delivery_weapon': expand_delivery_weapon,
    'named_mercenary_weapon': expand_named_merc_weapon,
    'aura_recipe': expand_aura_recipe,
    'qualified_equipment': expand_qualified_equipment,
    'named_throwing_weapon': expand_named_throwing,
    'mercenary_weapon': expand_merc_weapon,
    'player_combat_weapon': expand_combat_weapon,
    'original_sunder_charm': expand_sunder_charm,
    'charged_utility': expand_charge_utility,
    'unique_inventory_charm': expand_unique_inventory_charm,
    'merc_survival': expand_merc_survival,
    'player_footwear': expand_footwear,
    'named_player_utility': expand_named_utility,
    'player_progression_equipment': expand_progression_equipment,
}
