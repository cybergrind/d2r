"""First price strategies: fully known empty bases and exact affixed variants."""

import math

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.handlers.socket_fillers import compare_equipment_sockets
from pricing.knowledge.assessment.mechanics.affixed_charges import affixed_charge_properties
from pricing.knowledge.assessment.mechanics.affixed_cold import affixed_cold_properties
from pricing.knowledge.assessment.mechanics.affixed_per_level import affixed_per_level_properties
from pricing.knowledge.assessment.mechanics.affixed_poison import affixed_poison_properties
from pricing.knowledge.assessment.mechanics.affixed_triggers import affixed_trigger_properties
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier
from pricing.knowledge.assessment.mechanics.superior_quality import (
    superior_flat_damage,
    superior_roll_gaps,
    superior_without_ed,
)
from pricing.knowledge.assessment.property_equivalence import validate_finite_properties


class ReviewHandler:
    def __init__(self, reason):
        self.reason = reason

    def contract(self, facts, family):
        return None, [self.reason]


DEFENSE_FAMILIES = frozenset({'helm', 'armor', 'shield', 'accessory'})


def comparison_properties(facts, family, gaps):
    properties = dict(facts.properties)
    if family in DEFENSE_FAMILIES:
        defense = facts.stats.get('31:0', {})
        if (
            defense.get('status') != 'decoded'
            or type(defense.get('value')) not in (int, float)
            or not math.isfinite(defense['value'])
        ):
            gaps.append('Total defense is required for this armor comparison.')
        else:
            properties['1855'] = defense['value']
    try:
        validate_finite_properties(properties)
    except ValueError as error:
        gaps.append(str(error))
    return properties


def require_empty_contents(facts, gaps, filled_reason):
    if facts.socket_contents == 'empty':
        return
    reason = filled_reason if facts.socket_contents == 'filled' else 'socket_contents is unknown or unverified.'
    if reason not in gaps:
        gaps.append(reason)


def exact_contract(facts, family, policy, supported):
    gaps = [*facts.gaps, *facts.projection_gaps]
    affix_properties = {}
    if policy == 'affixed':
        consumed, effect_gaps = set(), []
        for project in (
            affixed_charge_properties,
            affixed_trigger_properties,
            affixed_per_level_properties,
            affixed_cold_properties,
            affixed_poison_properties,
        ):
            values, keys, errors = project(facts)
            for key, value in values.items():
                if key in affix_properties and affix_properties[key] != value:
                    effect_gaps.append(f'Affix effects conflict on market property {key}.')
                affix_properties[key] = value
            consumed |= keys
            effect_gaps.extend(errors)
        gaps = [g for g in gaps if g not in {f'No verified market mapping for native stat {key}.' for key in consumed}]
        gaps.extend(effect_gaps)
    if family not in supported:
        gaps.append(f'{family} comparison policy is not implemented for {policy} items.')
    if policy == 'affixed' and not facts.properties and not affix_properties:
        gaps.append('No comparable affix inventory.')
    flat_damage = policy == 'base' and family == 'weapon' and superior_flat_damage(facts)
    no_ed = policy == 'base' and family == 'weapon' and (superior_without_ed(facts) or flat_damage)
    no_defense = policy == 'base' and family in DEFENSE_FAMILIES and superior_without_ed(facts, 'armor')
    if (
        policy == 'base'
        and facts.rarity == 'superior'
        and family in DEFENSE_FAMILIES
        and '16:0' not in facts.stats
        and not no_defense
    ):
        gaps.append('Armor enhancement coverage is unproven.')
    needs_damage_coverage = policy == 'affixed' or (policy == 'base' and facts.rarity == 'superior')
    if needs_damage_coverage and family == 'weapon' and not {'17:0', '18:0'} <= facts.stats.keys() and not no_ed:
        gaps.append('Weapon damage-modifier coverage is unproven.')
    socket_comparison = compare_equipment_sockets(facts, family, policy)
    if socket_comparison is None:
        require_empty_contents(facts, gaps, 'Filled sockets require a contribution-aware comparison policy.')
    if policy == 'base' and family in DEFENSE_FAMILIES | {'weapon'}:
        quality_facts = socket_comparison.facts if socket_comparison else facts
        gaps.extend(superior_roll_gaps(quality_facts, 'weapons' if family == 'weapon' else 'armor'))
    properties = comparison_properties(facts, family, gaps)
    for key, value in affix_properties.items():
        if key in properties and properties[key] != value:
            gaps.append(f'Affix effect market property {key} conflicts with captured component.')
        properties[key] = value
    if no_defense:
        properties['425'] = 0
    if no_ed:
        properties['510'] = 0  # Proven quality identity; require explicit zero ED in listings.
    if flat_damage:
        properties['448'] = 1
    if gaps:
        return None, list(dict.fromkeys(gaps))
    return ComparableContract(
        1,
        policy,
        family,
        facts.base_name,
        facts.rarity,
        facts.ethereal,
        facts.sockets,
        facts.socket_contents,
        properties,
        base_code=facts.base_code,
        base_tier=base_tier(facts.base_code),
        socket_payload=socket_comparison.payload if socket_comparison else (),
    ), []


class BaseHandler:
    def contract(self, facts, family):
        return exact_contract(facts, family, 'base', {'weapon', 'helm', 'armor', 'shield', 'accessory'})


class AffixedHandler:
    def contract(self, facts, family):
        return exact_contract(
            facts, family, 'affixed', {'weapon', 'jewelry', 'helm', 'armor', 'shield', 'accessory', 'charm', 'jewel'}
        )
