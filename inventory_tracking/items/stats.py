"""Stat-family strategies with no memory access, market projection or rendering.

Dispatch selects a family before validating its payload. A decoder returns fields
for a decoded row, or None for an invalid/unsupported payload. None is terminal:
we never reinterpret a rejected specialized encoding as a generic scalar.
"""

from dataclasses import dataclass

from inventory_tracking.items.effects import (
    decode_magic_pierce,
    decode_quest_difficulty,
    decode_reanimate,
    decode_set_state,
    decode_visual_effect,
)
from inventory_tracking.items.poison import FRAMES_PER_SECOND
from inventory_tracking.items.stat_constants import (
    CHARGE_COUNT_BITS,
    CHARGE_COUNT_MASK,
    CHARGE_PAYLOAD_MAX,
    CLASS_ABBREVIATIONS,
    CLASS_NAMES,
    FLEE_SCALE,
    HIT_EFFECT_DESCRIPTION_FUNCTION,
    PERCENT_MAX,
    PROC_DESCRIPTION_FUNCTION,
    PROC_ENCODING,
    REPAIR_RATE_SCALE,
    SKILL_ELEMENTS,
    SKILL_LEVEL_BITS,
    SKILL_LEVEL_MASK,
    SKILL_TABS,
    SUNDER_MAGNITUDE,
    SUNDER_STATS,
    TOTAL_LABELS,
    StatId,
)


@dataclass(frozen=True)
class StatContext:
    stat: dict
    spec: dict
    skills: dict
    base: dict | None
    viewer_level: int | None = None

    @property
    def raw(self):
        return self.stat['raw']

    @property
    def layer(self):
        return self.stat['layer']

    def packed_skill(self):
        return self.skills.get(str(self.layer >> SKILL_LEVEL_BITS)), self.layer & SKILL_LEVEL_MASK


def decode_total(ctx):
    # Defense can be a signed modifier on weapons (Dimoak's Hew: -8).
    # Damage totals, durability and counters still require nonnegative values.
    if ctx.layer == 0 and (ctx.raw >= 0 or ctx.stat['id'] == StatId.DEFENSE):
        return {'value': ctx.raw, 'text': f'{TOTAL_LABELS[ctx.stat["id"]]}: {ctx.raw}'}
    return None


def decode_flee(ctx):
    if ctx.layer != 0 or not 0 < ctx.raw <= FLEE_SCALE:
        return None
    value = ctx.raw * 100 // FLEE_SCALE
    label = 'Hit Causes Monster to Flee +{{value}}%'
    return {'value': value, 'range_label': label, 'text': label.replace('{{value}}', str(value))}


def decode_hit_effect(ctx):
    """Level 1 renders as the bare effect name; higher levels append +N like the market label."""
    label = ctx.spec.get('label')
    if not label or ctx.layer != 0 or ctx.raw < 1:
        return None
    suffix = ' +{{value}}'
    if not label.endswith(suffix):
        return None
    text = label[: -len(suffix)] if ctx.raw == 1 else label.replace('{{value}}', str(ctx.raw))
    return {'value': ctx.raw, 'label': label, 'text': text}


def decode_repair(ctx):
    if ctx.layer == 0 and 0 < ctx.raw <= REPAIR_RATE_SCALE:
        seconds = REPAIR_RATE_SCALE // ctx.raw
        return {'value': seconds, 'text': f'Repairs 1 durability in {seconds} seconds'}
    return None


def decode_replenish_quantity(ctx):
    # D2MOO ItemMode.cpp sub_6FC4A350 uses this as a regeneration rate.
    # The tooltip has no magnitude; do not project the coefficient as a
    # market quantity or claim an exact modern-game replenishment interval.
    if ctx.layer == 0 and ctx.raw > 0:
        return {'value': ctx.raw, 'unit': 'replenishment_rate', 'text': 'Replenishes quantity'}
    return None


def decode_base_speed(ctx):
    if ctx.layer == 0 and ctx.base and ctx.base.get('category') == 'weapons' and ctx.base.get('speed') == -ctx.raw:
        return {
            'value': -ctx.raw,
            'text': f'Base weapon speed: {-ctx.raw} (lower is faster; not increased attack speed)',
        }
    return None


def decode_per_level(ctx):
    shift = ctx.spec.get('op_param')
    template = ctx.spec.get('template')
    if (
        ctx.layer != 0
        or type(ctx.viewer_level) is not int
        or not 1 <= ctx.viewer_level <= 99
        or type(shift) is not int
        or not 0 <= shift <= 16
        or ctx.raw < 0
        or not template
        or '%s' in template
        or ctx.spec.get('descfunc') != 19
    ):
        return None
    # Per-level coefficients also carry ValShift (8 for Life/Mana).
    # Keep fractional points until the final tooltip value is truncated.
    divisor = 1 << (shift + ctx.spec.get('shift', 0))
    value = ctx.raw * ctx.viewer_level // divisor
    return {
        'value': value,
        'text': (template % value) + ' (Based on Character Level)',
        'viewer_level': ctx.viewer_level,
        'per_level': {'numerator': ctx.raw, 'denominator': divisor},
        'origin': 'level_formula',
    }


def decode_cold_duration(ctx):
    if ctx.layer != 0 or ctx.raw < 0:
        return None
    seconds = ctx.raw / FRAMES_PER_SECOND
    return {
        'value': seconds,
        'unit': 'seconds',
        'presentation': 'internal',
        'text': f'Base cold duration: {seconds:g} seconds (before target/difficulty modifiers)',
    }


def decode_armor_movement(ctx):
    if (
        ctx.layer == 0
        and ctx.base
        and ctx.base.get('category') == 'armor'
        and ctx.base.get('movement_penalty') == -ctx.raw
    ):
        return {
            'value': ctx.raw,
            'text': f'Armor movement penalty: {ctx.raw}% (inherent base effect)',
            'presentation': 'internal',
            'origin': 'base_type',
        }
    return None


def decode_scalar(ctx):
    label = ctx.spec.get('label')
    divisor = 1 << ctx.spec.get('shift', 0)
    if not label or ctx.layer != 0 or ctx.raw % divisor:
        return None
    # A flag must assert presence; zero and non-boolean payloads stay unknown.
    if '{{value}}' not in label and ctx.raw != 1:
        return None
    value = ctx.raw // divisor
    return {'value': value, 'label': label, 'text': label.replace('{{value}}', str(value)).replace('+-', '-')}


def decode_sunder(ctx):
    label = ctx.spec.get('label')
    if ctx.layer == 0 and ctx.raw == SUNDER_MAGNITUDE and label:
        return {'value': ctx.raw, 'label': label, 'text': label}
    return None


def decode_charges(ctx):
    skill, level = ctx.packed_skill()
    remaining, maximum = ctx.raw & CHARGE_COUNT_MASK, ctx.raw >> CHARGE_COUNT_BITS
    if ctx.spec and skill and level and 0 <= ctx.raw <= CHARGE_PAYLOAD_MAX and remaining <= maximum:
        return {
            'text': f'Level {level} {skill["name"]} ({remaining}/{maximum} Charges)',
            'value': remaining,
            'unit': 'charges_remaining',
            'charges': {'remaining': remaining, 'maximum': maximum},
        }
    return None


def decode_proc(ctx):
    skill, level = ctx.packed_skill()
    template = ctx.spec.get('template')
    if skill and level and 0 <= ctx.raw <= PERCENT_MAX and template:
        return {'text': template % (ctx.raw, level, skill['name']), 'value': ctx.raw, 'unit': 'percent_chance'}
    return None


def decode_single_skill(ctx):
    skill = ctx.skills.get(str(ctx.layer))
    if not ctx.spec or not skill or ctx.raw <= 0:
        return None
    if ctx.stat['id'] == StatId.AURA:
        label = 'Level {{value}} ' + skill['name'] + ' Aura When Equipped'
    else:
        label = '+{{value}} to ' + skill['name']
        if ctx.stat['id'] == StatId.CLASS_SINGLE_SKILL:
            class_name = CLASS_ABBREVIATIONS.get(skill['class'], skill['class'])
            label += f' ({class_name} Only)'
    return {
        'value': ctx.raw,
        **({'range_label': label} if ctx.stat['id'] in (StatId.SINGLE_SKILL, StatId.AURA) else {}),
        'text': label.replace('{{value}}', str(ctx.raw)),
    }


def decode_throw_modifier(ctx):
    if ctx.layer != 0 or ctx.raw < 0:
        return None
    # d2data itemstatcost: 159/160 are the minimum/maximum throw components.
    endpoint = 'Minimum' if ctx.stat['id'] == 159 else 'Maximum'
    return {
        'value': ctx.raw,
        'text': f'{endpoint} throw damage modifier: +{ctx.raw} (internal weapon stat)',
        'presentation': 'internal',
    }


def decode_skill_tab(ctx):
    class_id, tree = divmod(ctx.layer, 8)
    if not 0 <= class_id < len(SKILL_TABS) or not 0 <= tree < 3 or ctx.raw <= 0:
        return None
    label = '+{{value}} to ' + SKILL_TABS[class_id][tree] + f' ({CLASS_NAMES[class_id]} Only)'
    return {'value': ctx.raw, 'label': label, 'text': label.replace('{{value}}', str(ctx.raw))}


def decode_magic_mastery(ctx):
    # d2data/allstrings-eng.json ModStrMagMastery (missing in the planner strings).
    if ctx.layer == 0:
        label = '+{{value}}% to Magic Skill Damage'
        return {
            'value': ctx.raw,
            'range_label': label,
            'text': label.replace('{{value}}', str(ctx.raw)).replace('+-', '-'),
        }
    return None


def decode_elemental_skills(ctx):
    element = SKILL_ELEMENTS.get(ctx.layer)
    if element and ctx.raw > 0:
        label = '+{{value}} to ' + element + ' Skills'
        return {'value': ctx.raw, 'range_label': label, 'text': label.replace('{{value}}', str(ctx.raw))}
    return None


def decode_class_skills(ctx):
    if ctx.spec and 0 <= ctx.layer < len(CLASS_NAMES) and ctx.raw > 0:
        return {'value': ctx.raw, 'text': f'+{ctx.raw} to {CLASS_NAMES[ctx.layer]} Skill Levels'}
    return None


# Add native-ID families here; metadata-defined encodings are selected below.
STAT_DECODERS = {
    56: decode_cold_duration,
    67: decode_armor_movement,
    98: decode_set_state,
    140: decode_visual_effect,
    155: decode_reanimate,
    159: decode_throw_modifier,
    160: decode_throw_modifier,
    181: decode_visual_effect,
    356: decode_quest_difficulty,
    358: decode_magic_pierce,
    **dict.fromkeys(TOTAL_LABELS, decode_total),
    **dict.fromkeys(SUNDER_STATS, decode_sunder),
    StatId.SELF_REPAIR: decode_repair,
    StatId.REPLENISH_QUANTITY: decode_replenish_quantity,
    StatId.FLEE: decode_flee,
    StatId.BASE_SPEED: decode_base_speed,
    StatId.CHARGES: decode_charges,
    StatId.SINGLE_SKILL: decode_single_skill,
    StatId.CLASS_SINGLE_SKILL: decode_single_skill,
    StatId.AURA: decode_single_skill,
    StatId.CLASS_SKILLS: decode_class_skills,
    StatId.ELEMENTAL_SKILLS: decode_elemental_skills,
    StatId.MAGIC_MASTERY: decode_magic_mastery,
    StatId.SKILL_TAB: decode_skill_tab,
}


def decode_stat(ctx):
    # D2MOO D2StatList.cpp op4/5 evaluate on the wielder. Op5 scales a
    # percentage, not flat damage; only display its coefficient-derived bonus.
    level_op = ctx.spec.get('op')
    if ctx.spec.get('op_base') == 'level' and (
        level_op == 2 or (ctx.stat['id'] in (214, 218) and level_op == 4) or (ctx.stat['id'] == 219 and level_op == 5)
    ):
        return decode_per_level(ctx)
    decoder = STAT_DECODERS.get(ctx.stat['id'])
    if decoder is None:
        if ctx.spec.get('encode') == PROC_ENCODING and ctx.spec.get('descfunc') == PROC_DESCRIPTION_FUNCTION:
            decoder = decode_proc
        elif ctx.spec.get('descfunc') == HIT_EFFECT_DESCRIPTION_FUNCTION:
            decoder = decode_hit_effect
        else:
            decoder = decode_scalar
    return decoder(ctx)


def derived_base_stats(base):
    """Base-type facts have no raw memory provenance or rolled market facets."""
    if not base or not base.get('undead_damage_bonus'):
        return []
    bonus = base['undead_damage_bonus']
    return [
        {
            'status': 'decoded',
            'origin': 'base_type',
            'value': bonus,
            'text': f'+{bonus}% Damage to Undead (inherent base-type bonus)',
        }
    ]
