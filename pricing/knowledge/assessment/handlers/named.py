"""Exact named-item comparisons with roll, base and defense safeguards."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.exact import comparison_properties, require_empty_contents
from pricing.knowledge.assessment.handlers.facet import (
    facet_fixed_damage,
    facet_fixed_duration,
    facet_fixed_poison,
    facet_trigger,
)
from pricing.knowledge.assessment.handlers.intrinsic import fixed_properties
from pricing.knowledge.assessment.handlers.property_groups import comparison_gaps as property_group_gaps
from pricing.knowledge.assessment.handlers.random_skills import comparison_gaps
from pricing.knowledge.assessment.handlers.seasonal import comparison_discriminators, shared_scalar_ranges
from pricing.knowledge.assessment.handlers.socket_fillers import compare_named_sockets
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier
from pricing.knowledge.assessment.mechanics.elemental import ENDPOINTS, fixed_elemental_properties
from pricing.knowledge.assessment.mechanics.enhanced_defense import capture_gap as enhanced_defense_gap
from pricing.knowledge.assessment.mechanics.flat_defense import capture_gap as flat_defense_gap
from pricing.knowledge.assessment.mechanics.named_charges import fixed_charge_properties
from pricing.knowledge.assessment.mechanics.named_cold import cold_duration_keys
from pricing.knowledge.assessment.mechanics.named_durability import capture_gap as durability_gap
from pricing.knowledge.assessment.mechanics.named_fixed_skills import fixed_skill_keys
from pricing.knowledge.assessment.mechanics.named_fixed_stats import (
    fixed_magic_damage_keys,
    fixed_repair_keys,
    fixed_scalar_keys,
)
from pricing.knowledge.assessment.mechanics.named_flags import fixed_flag_keys, native_ethereal_gap
from pricing.knowledge.assessment.mechanics.named_flat_damage import fixed_armor_damage_keys
from pricing.knowledge.assessment.mechanics.named_flee import capture_gap as flee_gap
from pricing.knowledge.assessment.mechanics.named_requirements import required_level
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps, variable_projection_gaps
from pricing.knowledge.assessment.mechanics.named_sockets import socket_gaps
from pricing.knowledge.assessment.mechanics.named_special_effects import special_effect_keys
from pricing.knowledge.assessment.mechanics.named_throwing import fixed_quantity_keys, throwing_damage_keys
from pricing.knowledge.assessment.mechanics.per_level import fixed_per_level_keys, variable_per_level_gaps
from pricing.knowledge.assessment.mechanics.plain_set_defense import capture_gap
from pricing.knowledge.assessment.mechanics.poison import POISON_KEYS, fixed_poison_range
from pricing.knowledge.assessment.mechanics.shield_blocking import modifier_facts
from pricing.knowledge.assessment.mechanics.triggers import named_trigger_properties
from pricing.knowledge.assessment.mechanics.variable_triggers import variable_trigger_properties
from pricing.knowledge.market_facet_catalog import facet_catalog


class NamedHandler:
    def contract(self, facts, family):
        gaps = [*facts.gaps, *facts.projection_gaps]
        definition, identity_gaps = resolve_named_definition(facts)
        if definition is None:
            return None, [*gaps, *identity_gaps]
        if gap := native_ethereal_gap(facts, definition):
            gaps.append(gap)
        gaps.extend(socket_gaps(facts, definition))
        if gap := durability_gap(facts, definition):
            gaps.append(gap)
        facet_identity = facet_catalog(definition) if facts.name == 'Rainbow Facet' else None
        if facts.name == 'Rainbow Facet' and facet_identity is None:
            return None, [*gaps, 'Facet native identity has no verified market catalog.']
        if family == 'shield':
            facts, block_gaps = modifier_facts(facts)
            if block_gaps:
                return None, [*gaps, *block_gaps]
        trigger_properties, consumed, trigger_gaps = facet_trigger(facts, definition)
        named_procs, proc_keys, proc_gaps = named_trigger_properties(facts, definition)
        variable_procs, trigger_levels, variable_keys, variable_gaps = variable_trigger_properties(facts, definition)
        trigger_properties.update(variable_procs)
        consumed |= variable_keys
        gaps.extend(variable_gaps)
        charged_properties, charge_keys, charge_gaps = fixed_charge_properties(facts, definition)
        trigger_properties.update(charged_properties)
        consumed |= charge_keys
        gaps.extend(charge_gaps)
        trigger_properties.update(named_procs)
        consumed |= proc_keys
        level_keys, level_gaps = fixed_per_level_keys(facts, definition)
        consumed |= level_keys
        gaps.extend(level_gaps)
        gaps.extend(variable_per_level_gaps(facts, definition))
        trigger_gaps.extend(proc_gaps)
        duration_keys, duration_gaps = facet_fixed_duration(facts, definition)
        poison_properties, poison_keys, poison_gaps = facet_fixed_poison(facts, definition)
        poison = definition.get('fixed_poison_effect') if facts.name != 'Rainbow Facet' else None
        if poison:
            damage = (
                fixed_poison_range(
                    facts, poison['minimum_rate_raw'], poison['maximum_rate_raw'], poison['duration_frames']
                )
                if poison.get('source_count') == 1
                else None
            )
            if damage is None:
                poison_gaps.append('Named fixed poison components are missing, changed or unverified.')
            else:
                poison_keys |= set(POISON_KEYS)
                if poison['minimum_rate_raw'] == poison['maximum_rate_raw']:
                    poison_properties['589'] = damage[0]
                elif '589' in facts.properties:
                    poison_gaps.append('A poison damage range cannot be compared as one scalar market value.')
        flag_keys, flag_gaps = fixed_flag_keys(facts, definition)
        consumed |= flag_keys
        scalar_keys, scalar_gaps = fixed_scalar_keys(facts, definition)
        consumed |= scalar_keys
        gaps.extend(scalar_gaps)
        repair_keys, repair_gaps = fixed_repair_keys(facts, definition)
        consumed |= repair_keys
        gaps.extend(repair_gaps)
        magic_keys, magic_gaps = fixed_magic_damage_keys(facts, definition)
        consumed |= magic_keys
        gaps.extend(magic_gaps)
        skill_keys, skill_gaps = fixed_skill_keys(facts, definition)
        consumed |= skill_keys
        gaps.extend(skill_gaps)
        effect_keys, effect_gaps = special_effect_keys(facts, definition)
        consumed |= effect_keys
        gaps.extend(effect_gaps)
        flat_damage_keys, flat_damage_gaps = fixed_armor_damage_keys(facts, definition, family)
        consumed |= flat_damage_keys
        gaps.extend(flat_damage_gaps)
        quantity_keys, quantity_gaps = fixed_quantity_keys(facts, definition)
        consumed |= quantity_keys
        gaps.extend(quantity_gaps)
        throwing_keys, throwing_gaps = throwing_damage_keys(facts, definition)
        consumed |= throwing_keys
        gaps.extend(throwing_gaps)
        gaps.extend(flag_gaps)
        native_cold_keys, native_cold_gaps = cold_duration_keys(facts, definition)
        consumed |= native_cold_keys
        gaps.extend(native_cold_gaps)
        consumed |= duration_keys | poison_keys
        effects = definition.get('fixed_elemental_effects', ()) if facts.name != 'Rainbow Facet' else ()
        elemental = fixed_elemental_properties(facts, effects)
        for kind in {effect['kind'] for effect in effects}:
            if not {prop for _, prop in ENDPOINTS[kind]} <= elemental.keys():
                gaps.append(f'Named fixed {kind} damage components are missing, changed or unverified.')
            elif kind == 'cold':
                consumed.add('56:0')
        gaps.extend(poison_gaps)
        gaps.extend(duration_gaps)
        gaps = [g for g in gaps if g not in {f'No verified market mapping for native stat {key}.' for key in consumed}]
        gaps.extend(trigger_gaps)
        if facts.rarity == 'set' and facts.ethereal is not False:
            gaps.append('Set item ethereal state conflicts with game definitions or is unknown.')
        socket_comparison = compare_named_sockets(facts, definition, family)
        if socket_comparison is None:
            require_empty_contents(
                facts, gaps, 'Filled named sockets require verified contribution and contents comparisons.'
            )
        gaps.extend(roll_gaps(socket_comparison.facts if socket_comparison else facts, definition))
        if gap := flee_gap(socket_comparison.facts if socket_comparison else facts, definition):
            gaps.append(gap)
        if (facts.socket_contents == 'empty' or socket_comparison) and (
            gap := flat_defense_gap(socket_comparison.facts if socket_comparison else facts, definition, family)
        ):
            gaps.append(gap)
        gaps.extend(comparison_gaps(facts, definition))
        if (facts.socket_contents == 'empty' or socket_comparison) and (
            gap := enhanced_defense_gap(socket_comparison.facts if socket_comparison else facts, definition, family)
        ):
            gaps.append(gap)
        if defense_gap := capture_gap(facts):
            gaps.append(defense_gap)
        properties = comparison_properties(facts, family, gaps)
        for key, value in {**trigger_properties, **poison_properties}.items():
            if key in properties and properties[key] != value:
                gaps.append(f'Facet market property {key} conflicts with captured component.')
            else:
                properties[key] = value
        gaps.extend(variable_projection_gaps(facts, definition, properties))
        gaps.extend(property_group_gaps(facts, definition, properties))
        fixed_damage, damage_gaps = facet_fixed_damage(facts, definition)
        gaps.extend(damage_gaps)
        if gaps:
            return None, list(dict.fromkeys(gaps))
        properties.update(comparison_discriminators(definition, facts))
        return ComparableContract(
            1,
            'named',
            family,
            facts.name,
            facts.rarity,
            facts.ethereal,
            facts.sockets,
            facts.socket_contents,
            properties,
            socket_payload=socket_comparison.payload if socket_comparison else (),
            base_code=facts.base_code,
            base_tier=base_tier(facts.base_code),
            required_level=required_level(facts, definition),
            catalog_id=facet_identity[0] if facet_identity else None,
            trigger_levels=trigger_levels,
            intrinsic_properties={
                **(trigger_properties if facet_identity else {}),
                **fixed_properties(facts, shared_scalar_ranges(definition, facts)),
                **fixed_damage,
                **elemental,
                **poison_properties,
                **named_procs,
                **charged_properties,
            },
        ), []
