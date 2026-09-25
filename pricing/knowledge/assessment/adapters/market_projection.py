"""Reviewed native identities missing from the decoder's scalar market facets.

Verified against pricing/data/appraisal-properties.json (2026-09-24).
Parameters are part of identity: class skills, skill tabs, staffmods, oskills and
wearer auras must never share a projection merely because their skill names match.
Values here are decoded units (not encoded raw values, especially Flee).
"""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact


CATALOG = Path(__file__).resolve().parents[1] / 'rules/native_market_properties.json'


@lru_cache(maxsize=2)
def compiled_properties(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported native market projection schema')
    return {key: row['property_id'] for key, row in document['mappings'].items()}


NATIVE_PROPERTIES = {
    '75:0': '937',  # Maximum durability percent, verified cached numeric field.
    '126:1': '586',  # All-class Fire Skills, not Sorceress Fire skill tab 188:8
    '48:0': '458',  # Minimum Fire Damage
    '49:0': '459',  # Maximum Fire Damage
    '50:0': '478',  # Minimum Lightning Damage
    '51:0': '479',  # Maximum Lightning Damage
    '54:0': '482',  # Minimum Cold Damage; duration is a separate stat
    '55:0': '483',  # Maximum Cold Damage
    '329:0': '750',  # Fire Skill Damage
    '330:0': '743',  # Lightning Skill Damage
    '331:0': '747',  # Cold Skill Damage
    '332:0': '783',  # Poison Skill Damage, not poison damage per frame
    '333:0': '735',  # Enemy Fire Resistance reduction
    '334:0': '736',  # Enemy Lightning Resistance reduction
    '335:0': '609',  # Enemy Cold Resistance reduction
    '336:0': '723',  # Enemy Poison Resistance reduction
    '83:3': '442',  # Paladin skill levels
    '188:9': '516',  # Sorceress Lightning tab
    '188:10': '517',  # Sorceress Cold tab
    '107:56': '943',  # Meteor (Sorceress Only)
    '112:0': '534',  # Flee percentage, raw 128 means 100%
    '151:120': '859',  # Meditation aura level when equipped
    '97:9': '1210',  # Critical Strike (Any Class), not Amazon staffmod 858
}


def market_properties():
    return {**compiled_properties(read_artifact(CATALOG)), **NATIVE_PROPERTIES}


def project_native(key, row, properties, projected, gaps, catalog):
    property_id = catalog.get(key)
    value = row.get('value')
    if not property_id or row.get('status') != 'decoded' or type(value) not in (int, float):
        return
    if key in projected and projected[key] != property_id:
        gaps.append(f'Market projection conflicts for native stat {key}.')
        properties.pop(projected.pop(key), None)
        return
    if property_id in properties and (projected.get(key) != property_id or properties[property_id] != value):
        gaps.append(f'Market property {property_id} conflicts with native stat {key}.')
        properties.pop(property_id, None)
        projected.pop(key, None)
        return
    properties[property_id] = value
    projected[key] = property_id
