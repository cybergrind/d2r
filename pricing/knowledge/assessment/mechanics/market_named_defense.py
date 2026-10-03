"""Reviewed variant evidence for exact comparisons, without rewriting cached rows."""

from pricing.knowledge.assessment.mechanics.gore_rider_defense import VARIANT_MODE, variant_code
from pricing.knowledge.assessment.mechanics.plain_set_defense import with_evidence as set_defense_evidence
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES
from pricing.knowledge.assessment.mechanics.waterwalk_defense import (
    VARIANT_MODE as WATERWALK_MODE,
    variant_code as waterwalk_code,
)


def with_variant_evidence(contract, row):
    if (contract or {}).get('rarity') == 'set':
        return set_defense_evidence(contract, row)
    name = (contract or {}).get('name')
    models = {
        'Gore Rider': (VARIANT_MODE, variant_code, ('xhb', 'uhb')),
        'Waterwalk': (WATERWALK_MODE, waterwalk_code, ('xvb', 'uvb')),
    }
    if name not in models:
        return row
    mode, infer_code, codes = models[name]
    if (
        not contract
        or contract.get('policy') != 'named'
        or (contract.get('rarity'), contract.get('name')) != ('unique', name)
        or contract.get('ethereal') is not False
        or contract.get('base_code') not in codes
        or (row.get('rarity'), row.get('name')) != ('unique', name)
    ):
        return row
    code = infer_code(row)
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
        'model': mode,
        'observed_properties': {key: row['properties'][key] for key in ('425', '1855')},
        'native_hashes': dict(NATIVE_HASHES),
    }
    basis = {**row.get('facet_basis', {}), 'ethereal': proof}
    if row.get('base_code') is None:
        basis['base_code'] = proof
    return {**row, 'base_code': code, 'base_upgrade': code == codes[1], 'ethereal': False, 'facet_basis': basis}
