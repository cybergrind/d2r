"""Whole-basket asking references, never prices for an individual component."""

from pricing.knowledge.assessment.comparables import price_from_comparables
from pricing.knowledge.assessment.observations import superseded_rows
from pricing.knowledge.assessment.policies.quest_materials import KEYS, STATUES
from pricing.knowledge.market import scope_status, valid_positive


# Exact identities verified in the cached Traderie catalog; a 3x3 set is not 1x3.
SETS = {
    '3x3 Key Set': ('3357156195', '3 of each key; 9 keys total'),
    'Statue Set': ('1002230133766', 'one of each of the five statues'),
}
ENVELOPE = {'799', '800', '798', '1854', '933', '934'}


def relevant_set(contract):
    if not contract or contract.get('policy') != 'quest_material':
        return None
    code = contract.get('base_code')
    return '3x3 Key Set' if code in KEYS else 'Statue Set' if code in STATUES else None


def set_quote(name, rows, *, today):
    catalog_id, quantity_label = SETS[name]
    rows = list(rows)
    superseded = superseded_rows(rows)
    accepted, seen = [], set()
    for index, row in enumerate(rows):
        identity = row.get('listing_id'), row.get('observed_at')
        properties = row.get('properties', {})
        status = row.get('listing_status', {})
        if (
            index in superseded
            or identity in seen
            or row.get('name') != name
            or str(row.get('catalog_id')) != catalog_id
            or row.get('category') != 'misc'
            or row.get('scope_status') != 'verified'
            or scope_status(properties) != 'verified'
            or set(properties) - ENVELOPE
            or row.get('evidence_kind') != 'ask'
            or status.get('active') is not True
            or status.get('selling') is not True
            or status.get('completed') is not False
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or not row.get('seller_id')
            or not row.get('listing_id')
            or not valid_positive(row.get('ask_ist'))
        ):
            continue
        seen.add(identity)
        accepted.append(row)
    return {
        'name': name,
        'quantity_label': quantity_label,
        'liquidity': 'unverified',
        'estimate': price_from_comparables(
            {'contract': {'policy': 'commodity_set', 'name': name}, 'accepted': accepted}, today=today
        ),
    }
