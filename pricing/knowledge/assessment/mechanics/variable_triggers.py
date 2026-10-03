"""Preserve native item-level proc levels through exact listing comparison."""

from collections.abc import Mapping
from math import trunc

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.mechanics.triggers import MARKET_FIELDS
from pricing.knowledge.named_triggers import EVENTS


EVENT_LABELS = {
    195: 'on attack',
    196: 'when you Kill an Enemy',
    197: 'when you Die',
    198: 'on striking',
    199: 'when you Level-Up',
    201: 'when struck',
}


def proc_level(item_level, required, maximum, parameter):
    """PropertyFunc11, including C++ truncation toward zero before clamping."""
    if parameter == 0:
        return min(maximum if maximum > 0 else 20, max(1, trunc((item_level - required) / 4) + 1))
    divisor = max(1, -trunc(max(1, 99 - required) / parameter))
    return max(1, trunc((item_level - required) / divisor)) & 63


def variable_trigger_properties(facts, definition):
    catalog = metadata()
    skills = catalog['skills']
    stat_ids = {r['name']: int(k) for k, r in catalog['stats'].items()}
    record = definition.get('game_definition', {})
    props, levels, consumed, gaps = {}, {}, set(), []
    for slot in range(1, 13):
        code, parameter = record.get(f'prop{slot}'), record.get(f'max{slot}')
        if not isinstance(code, str) or code.casefold() not in EVENTS or type(parameter) is not int or parameter > 0:
            continue
        stat = stat_ids[EVENTS[code.casefold()]]
        skill = record.get(f'par{slot}')
        if isinstance(skill, str):
            matches = [
                int(k) for k, v in skills.items() if skill.casefold() == v.get('internal_name', v['name']).casefold()
            ]
            skill = matches[0] if len(matches) == 1 else None
        spec = skills.get(str(skill), {})
        chance = record.get(f'min{slot}')
        if type(skill) is not int or not spec or type(chance) is not int:
            gaps.append(f'Variable trigger definition {slot} is unverified.')
            continue
        chance = chance if chance > 0 else 5
        required, maximum = spec.get('required_level'), spec.get('maximum_level')
        rows = [
            (k, v)
            for k, v in facts.stats.items()
            if v.get('id') == stat and type(v.get('parameter')) is int and v['parameter'] // 64 == skill
        ]
        if type(required) is not int or type(maximum) is not int or len(rows) != 1:
            gaps.append(f'Variable trigger {stat}:{skill} is missing or ambiguous.')
            continue
        key, row = rows[0]
        level = row['parameter'] & 63
        item_levels = [facts.item_level] if facts.item_level is not None else range(1, 100)
        allowed = {proc_level(ilvl, required, maximum, parameter) for ilvl in item_levels}
        prop = MARKET_FIELDS.get((stat, skill))
        if (
            row.get('status') != 'decoded'
            or row.get('unit') != 'percent_chance'
            or type(row.get('raw')) is not int
            or row['raw'] != chance
            or type(row.get('value')) not in (int, float)
            or row['value'] != chance
            or not 1 <= chance <= 100
            or not 1 <= level <= 63
            or level not in allowed
            or row.get('market_property') not in (None, prop)
        ):
            gaps.append(f'Variable trigger {stat}:{skill} has conflicting chance, level or native identity.')
        elif prop is None:
            gaps.append(f'Variable trigger {stat}:{skill} has no verified market field.')
        elif prop in levels:
            gaps.append(f'Variable trigger {stat}:{skill} duplicates a market field.')
        else:
            props[prop], levels[prop] = chance, level
            consumed.add(key)
    return ({}, {}, set(), gaps) if gaps else (props, levels, consumed, [])


def listing_level_gaps(levels, chances, listing):
    """Require the explicit raw template; chance alone never supplies a level."""
    reverse = {prop: (stat, skill) for (stat, skill), prop in MARKET_FIELDS.items()}
    gaps = []
    for prop, expected in levels.items():
        identity = reverse.get(prop)
        rows = [r for r in listing.get('raw_properties', []) if str(r.get('property_id')) == prop]
        if identity is None or len(rows) != 1:
            gaps.append(f'Proc level {prop} is missing or ambiguous in listing evidence.')
            continue
        stat, skill = identity
        name = metadata()['skills'].get(str(skill), {}).get('name')
        label = f'{{{{value}}}}% Chance to cast level {{{{level}}}} {name} {EVENT_LABELS.get(stat)}'
        row = rows[0]
        format_value = row.get('format')
        template = format_value.get('template') if isinstance(format_value, Mapping) else None
        level = template.get('level') if isinstance(template, Mapping) else None
        if (
            type(level) is not int
            or level != expected
            or row.get('property') != label
            or row.get('type') != 'number'
            or type(row.get('number')) not in (int, float)
            or row['number'] != chances.get(prop)
            or listing.get('properties', {}).get(prop) != chances.get(prop)
        ):
            gaps.append(f'Proc level/chance {prop} differs or lacks verified listing evidence.')
    return gaps
