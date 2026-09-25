"""Completed runewords compare by recipe, actual base and captured total rolls."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.handlers.exact import comparison_properties
from pricing.knowledge.assessment.handlers.intrinsic import fixed_properties
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier
from pricing.knowledge.assessment.mechanics.elemental import fixed_elemental_properties
from pricing.knowledge.assessment.mechanics.named_charges import fixed_charge_properties
from pricing.knowledge.assessment.mechanics.per_level import fixed_per_level_keys, variable_per_level_properties
from pricing.knowledge.assessment.mechanics.poison import POISON_KEYS, fixed_poison_total
from pricing.knowledge.assessment.mechanics.rune_physical import fixed_physical_rune_keys
from pricing.knowledge.assessment.mechanics.runeword_rolls import variable_roll_gaps
from pricing.knowledge.assessment.mechanics.triggers import named_trigger_properties
from pricing.knowledge.definition_store import catalog


def definitions():
    return catalog().runewords


def elemental_effects(definition, family):
    return [
        *definition.get('fixed_elemental_effects', ()),
        *definition.get('socket_compound_effects', {}).get(family, ()),
    ]


def intrinsic_properties(facts, definition, family):
    """Only unchanged, decoded, explicitly projected fixed recipe bonuses.

    Includes portable rune effects and verified shield-base blocking. Other
    base/staffmod contributions remain explicit; variable modifiers never become intrinsic.
    """
    ranges = {k: dict(v) for k, v in definition.get('roll_ranges', {}).items()}
    contributions = [definition.get('socket_bonus_ranges', {}).get(family, {})]
    if family == 'shield':
        contributions.append(definition.get('base_stat_ranges', {}).get(facts.base_code, {}))
    for contribution in contributions:
        for key, spec in contribution.items():
            if key in ranges:
                ranges[key]['min'] += spec['min']
                ranges[key]['max'] += spec['max']
            else:
                ranges[key] = dict(spec)
    effects = elemental_effects(definition, family)
    return {**fixed_properties(facts, ranges), **fixed_elemental_properties(facts, effects)}


def fixed_rune_poison(facts, definition, family):
    effects = definition.get('socket_compound_effects', {}).get(family, ())
    poisons = [effect for effect in effects if effect.get('kind') == 'poison']
    if len(poisons) != 1 or poisons[0].get('source_count') != 1:
        return {}
    effect = poisons[0]
    total = fixed_poison_total(
        facts, effect.get('minimum_rate_raw'), effect.get('maximum_rate_raw'), effect.get('duration_frames')
    )
    return {} if total is None else {'589': total}


class RunewordHandler:
    def contract(self, facts, family):
        gaps = [*facts.gaps, *facts.projection_gaps]
        base_rarity = 'low quality' if facts.rarity == 'low_quality' else facts.rarity
        if base_rarity not in ('normal', 'superior', 'low quality'):
            gaps.append('Runeword base quality is unknown or incompatible.')
        definition = definitions().get(facts.runeword)
        if not definition:
            return None, ['Runeword definition is absent from the offline KB.']
        triggers, consumed, trigger_gaps = named_trigger_properties(facts, definition)
        charges, charge_keys, charge_gaps = fixed_charge_properties(facts, definition)
        consumed |= charge_keys
        consumed |= fixed_physical_rune_keys(facts, definition, family)
        gaps.extend(charge_gaps)
        level_keys, level_gaps = fixed_per_level_keys(facts, definition)
        consumed |= level_keys
        gaps.extend(level_gaps)
        level_properties, variable_keys, variable_gaps = variable_per_level_properties(facts, definition)
        consumed |= variable_keys
        gaps.extend(variable_gaps)
        gaps = [g for g in gaps if g not in {f'No verified market mapping for native stat {key}.' for key in consumed}]
        gaps.extend(trigger_gaps)
        if facts.base_code not in definition['base_codes']:
            gaps.append('Captured base is incompatible with the runeword definition.')
        if facts.sockets != len(definition['runes']) or facts.socket_contents != 'filled':
            gaps.append('Socket count/contents disagree with the completed runeword.')
        gaps.extend(variable_roll_gaps(facts, definition, family))
        poison = fixed_rune_poison(facts, definition, family)
        if poison:
            consumed = {f'No verified market mapping for native stat {key}.' for key in POISON_KEYS}
            gaps = [gap for gap in gaps if gap not in consumed]
        properties = comparison_properties(facts, family, gaps)
        properties.update(level_properties)
        for key, value in charges.items():
            if key in properties and properties[key] != value:
                gaps.append(f'Runeword charge market property {key} conflicts with captured skill level.')
            else:
                properties[key] = value
        for key, value in triggers.items():
            if key in properties and properties[key] != value:
                gaps.append(f'Runeword trigger market property {key} conflicts with captured chance.')
            else:
                properties[key] = value
        for key, value in poison.items():
            if key in properties and properties[key] != value:
                gaps.append('Rune poison market value conflicts with captured components.')
            else:
                properties[key] = value
        intrinsic = intrinsic_properties(facts, definition, family)
        elemental = fixed_elemental_properties(facts, elemental_effects(definition, family))
        if {'482', '483'} <= elemental.keys():
            gaps = [gap for gap in gaps if gap != 'No verified market mapping for native stat 56:0.']
        if gaps:
            return None, list(dict.fromkeys(gaps))
        return ComparableContract(
            1,
            'runeword',
            family,
            facts.runeword,
            'runeword',
            facts.ethereal,
            facts.sockets,
            'filled',
            properties,
            base_code=facts.base_code,
            base_tier=base_tier(facts.base_code),
            base_rarity=base_rarity,
            intrinsic_properties={**intrinsic, **poison, **triggers, **charges},
        ), []
