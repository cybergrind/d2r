"""Require native compound recipe totals before constructing a price contract."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.elemental import ENDPOINTS, cold_duration_matches


SOURCE = Path(__file__).resolve().parents[4] / 'third-parties/d2data/json/runes.json'


@lru_cache(maxsize=2)
def recipes(raw):
    return json.loads(raw)


def compound_recipe_gaps(facts, definition, effects):
    record = recipes(read_artifact(SOURCE)).get(definition.get('name'))
    if record is None:
        return ['Native runeword recipe is absent from the pinned source.']
    slots = {slot for slot in range(1, 13) if record.get(f'T1Code{slot}') == 'dmg-elem'}
    if not slots:
        return []
    compiled = definition.get('fixed_elemental_effects', ())
    if any({e['kind'] for e in compiled if e.get('slot') == slot} != set(ENDPOINTS) for slot in slots):
        return ['Compound elemental recipe definitions need an offline rebuild.']
    gaps = []
    for kind, endpoints in ENDPOINTS.items():
        sources = [e for e in effects if e.get('kind') == kind]
        for (stat, prop), field in zip(endpoints, ('minimum_damage', 'maximum_damage'), strict=True):
            values = [e.get(field) for e in sources]
            if any(type(v) is not int or v < 0 for v in values):
                gaps.append(f'Compound elemental {kind} sources are unverified.')
                continue
            expected = sum(values)
            row = facts.stats.get(f'{stat}:0', {})
            if (
                row.get('status') != 'decoded'
                or type(row.get('raw')) is not int
                or row['raw'] != expected
                or type(row.get('value')) not in (int, float)
                or row['value'] != expected
                or type(facts.properties.get(prop)) not in (int, float)
                or facts.properties[prop] != expected
            ):
                gaps.append(f'Compound elemental {kind} endpoint {stat} is missing or conflicting.')
        if kind == 'cold':
            if len(sources) != 1 or type(sources[0].get('duration_frames')) is not int:
                gaps.append('Compound recipe cold duration requires verified native and market comparisons.')
            elif not cold_duration_matches(facts, sources[0]['duration_frames']):
                gaps.append('Compound recipe cold duration is missing or conflicting.')
    return gaps
