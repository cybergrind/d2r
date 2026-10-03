"""Original/upgraded totals for reviewed sets with no item defense bonuses."""

import hashlib
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES


ROOT = Path(__file__).resolve().parents[4]
BASES = {
    "Aldur's Advance": (('xtb', 39, 47), ('utb', 59, 68)),
    "Horazon's Hold": (('xlg', 28, 35), ('ulg', 54, 62)),
}
# Neither standalone nor item-specific partial-set properties add defense.
# Global equipped-set defense is a character bonus, not the item's total.
SET_HASH = 'c9987086caa820e8642149248d3138d3ebb89215f971525aec8e20e97fac4c5b'
HASHES = {'armor': NATIVE_HASHES['armor'], 'setitems': SET_HASH}


def variant_code(row):
    props = row.get('properties', {})
    if (
        row.get('name') not in BASES
        or row.get('rarity') != 'set'
        or row.get('ethereal') is not False
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or any(key in props for key in ('399', '425', '934'))
        or ('738' in props and props['738'] is not False)
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or type(props.get('1855')) is not int
    ):
        return None
    try:
        if any(
            hashlib.sha256(read_artifact(ROOT / 'third-parties/d2data/json' / f'{name}.json')).hexdigest() != digest
            for name, digest in HASHES.items()
        ):
            return None
    except OSError:
        return None
    for index, (code, low, high) in enumerate(BASES[row['name']]):
        upgraded = bool(index)
        if (
            low <= props['1855'] <= high
            and row.get('base_code') in (None, code)
            and props.get('930') in (None, 'Elite' if upgraded else 'Exceptional')
            and all(v is None or v is upgraded for v in (row.get('base_upgrade'), props.get('1216')))
        ):
            return code
    return None


def with_evidence(contract, row):
    name = (contract or {}).get('name')
    if name not in BASES or contract.get('policy') != 'named' or contract.get('rarity') != 'set':
        return row
    if (row.get('rarity'), row.get('name')) != ('set', name):
        return row
    code = variant_code(row)
    if code is None:
        return {
            **row,
            'mechanics_conflicts': [
                *row.get('mechanics_conflicts', ()),
                f'{name} defense and variant evidence is incomplete or conflicting.',
            ],
        }
    proof = {
        'kind': 'reviewed_named_defense',
        'model': 'plain_set_defense',
        'observed_properties': {'1855': row['properties']['1855']},
        'native_hashes': dict(HASHES),
    }
    return {
        **row,
        'base_code': code,
        'base_upgrade': code == BASES[name][1][0],
        'facet_basis': {**row.get('facet_basis', {}), 'base_code': proof},
    }


def capture_gap(facts):
    if facts.rarity != 'set' or facts.name not in BASES:
        return None
    defense = facts.stats.get('31:0', {})
    props = dict(facts.properties)
    if defense.get('status') == 'decoded':
        props['1855'] = defense.get('value')
    row = {
        'name': facts.name,
        'rarity': facts.rarity,
        'base_code': facts.base_code,
        'ethereal': facts.ethereal,
        'sockets': facts.sockets,
        'socket_contents': facts.socket_contents,
        'properties': props,
    }
    if variant_code(row) != facts.base_code or facts.base_code is None:
        return 'Named set total defense is missing or conflicts with its native base.'
    return None
