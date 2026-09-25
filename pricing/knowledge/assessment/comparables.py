"""Symmetric variant matching with retained rejection diagnostics, no price multipliers."""

from collections import Counter
from datetime import UTC, date, datetime

from pricing.knowledge.assessment.mechanics.sunder import listing_penalties
from pricing.knowledge.assessment.observations import superseded_rows
from pricing.knowledge.assessment.property_equivalence import canonical_properties
from pricing.knowledge.market import scope_status, summarize, valid_positive
from pricing.knowledge.names import normalize_name


# Verified normalization fields in market.normalize_listing; everything else is
# an item property until an explicit adapter proves it irrelevant to comparison.
# Catalog field933 is listing Region; the configured SC/NL/PC/RotW scope has
# no region restriction. It is not a rolled item modifier.
ENVELOPE_PROPERTIES = frozenset({'402', '738', '797', '798', '799', '800', '1854', '933', '934'})
SCOPE_PROPERTIES = frozenset({'798', '799', '800', '1854'})
MIN_SELLERS = 3
MAX_AGE_DAYS = 30  # Conservative publication default; disclosed, not a market fact.
MAX_DISPERSION = 5


def reject_reasons(contract, row):
    if not contract:
        return ['No supported, complete item comparison contract.']
    reasons = list(row.get('mechanics_conflicts', []))
    properties = {str(k): v for k, v in row.get('properties', {}).items()}
    if row.get('scope_status') != 'verified' or (
        SCOPE_PROPERTIES & properties.keys() and scope_status(properties) != 'verified'
    ):
        reasons.append('Unverified or incompatible SC/NL/PC/RotW scope.')
    if normalize_name(row.get('name')) != normalize_name(contract['name']):
        reasons.append('Different base identity.')
    if contract.get('base_code') and row.get('base_code') != contract['base_code']:
        reasons.append('Different or unknown runeword base.')
    for key in ('rarity', 'ethereal', 'sockets', 'socket_contents'):
        observed = row.get(key)
        expected = contract[key]
        if key == 'sockets':
            valid = type(observed) in (int, float) and observed == expected
        else:
            valid = type(observed) is type(expected) and observed == expected
        if not valid:
            reasons.append(f'{key}: expected {expected!r}, observed {observed!r}.')
    payload = contract.get('socket_payload')
    if payload:
        description = properties.get('934')
        if type(description) is not str or sorted(p.strip() for p in description.split(',')) != sorted(payload):
            reasons.append('Different or unverified socket filler identity.')
    envelope = ENVELOPE_PROPERTIES
    if '796' in properties:
        level = contract.get('required_level')
        if type(level) is int and type(properties['796']) is int and properties['796'] == level:
            envelope = envelope | {'796'}
        else:
            reasons.append('Listing required level is conflicting or unverified.')
    if contract['policy'] == 'runeword':
        envelope = envelope | set(row.get('base_selector_properties', []))
        quality = contract.get('base_rarity')
        if quality not in ('normal', 'superior', 'low quality') or row.get('base_rarity') != quality:
            reasons.append('Different or unknown runeword base quality.')
        if '1281' in properties:
            if properties['1281'] == quality and row.get('base_rarity') == quality:
                envelope = envelope | {'1281'}
            else:
                reasons.append('Runeword base quality property conflicts with the comparison.')
    if (
        contract['policy'] == 'named'
        and type(properties.get('1216')) is bool
        and row.get('base_upgrade') is properties['1216']
        and row.get('facet_basis', {}).get('base_code', {}).get('kind') == 'named_base_tier'
    ):
        envelope = envelope | {'1216'}
    if '930' in properties:
        tier = contract.get('base_tier')
        if tier in ('Normal', 'Exceptional', 'Elite') and properties['930'] == tier:
            envelope = envelope | {'930'}
        else:
            reasons.append('Listing base tier is conflicting or unverified.')
    modifiers = {k: v for k, v in properties.items() if k not in envelope}
    try:
        expected_properties = canonical_properties(contract['properties'])
        modifiers = canonical_properties(listing_penalties(contract, row, modifiers))
        if contract['policy'] in ('runeword', 'named'):
            intrinsic = canonical_properties(contract.get('intrinsic_properties', {}))
            for key, value in intrinsic.items():
                if key in expected_properties and value == expected_properties[key]:
                    modifiers.setdefault(key, value)
        if modifiers != expected_properties or any(
            type(modifiers[k]) is bool or type(v) is bool for k, v in expected_properties.items() if k in modifiers
        ):
            reasons.append('Missing, changed or extra item properties; exact modifier combination required.')
    except ValueError as error:
        reasons.append(str(error))
    if row.get('evidence_kind') != 'ask':
        reasons.append('Observation is not a normalized ask.')
    if row.get('unit_policy') != 'single_item' or not row.get('seller_id') or not valid_positive(row.get('ask_ist')):
        reasons.append('Ambiguous unit, missing seller or invalid price.')
    return reasons


def evaluate(contract, rows):
    accepted, rejected = [], []
    seen = set()
    rows = list(rows)
    superseded = superseded_rows(rows)
    for index, row in enumerate(rows):
        reasons = (
            ['Listing snapshot superseded by a later observation.']
            if index in superseded
            else reject_reasons(contract, row)
        )
        identity = (row.get('listing_id'), row.get('observed_at'))
        if row.get('listing_id') and identity in seen:
            reasons.append('Duplicate listing snapshot.')
        if row.get('listing_id'):
            seen.add(identity)
        if reasons:
            rejected.append(
                {
                    'listing_id': row.get('listing_id'),
                    'seller_id': row.get('seller_id'),
                    'source': row.get('source'),
                    'reasons': reasons,
                }
            )
        else:
            accepted.append(row)
    return {'contract': contract, 'summary': summarize(accepted), 'accepted': accepted, 'rejected': rejected}


def publication_rows(rows, today):
    """Separate dated evidence eligible now without mutating variant diagnostics."""
    fresh, excluded = [], Counter()
    for row in rows:
        try:
            observed = date.fromisoformat(row['observed_at'][:10])
        except KeyError, TypeError, ValueError:
            excluded['undated'] += 1
            continue
        age = (today - observed).days
        if age < 0:
            excluded['future'] += 1
        elif age > MAX_AGE_DAYS:
            excluded['stale'] += 1
        else:
            fresh.append(row)
    return fresh, dict(excluded)


def independent_asks(rows):
    """Retain the cheapest eligible ask per seller, with its actual provenance."""
    sellers = {}
    for row in sorted(rows, key=lambda r: (r['ask_ist'], str(r['seller_id']), str(r.get('listing_id', '')))):
        sellers.setdefault(row['seller_id'], row)
    return [
        {key: row.get(key) for key in ('seller_id', 'listing_id', 'ask_ist', 'observed_at', 'source', 'conversion')}
        for row in sellers.values()
    ]


def price_from_comparables(comparables, *, today=None):
    today = today or datetime.now(UTC).date()
    eligible, excluded = publication_rows(comparables['accepted'], today)
    summary = summarize(eligible)
    result = {
        'estimate_ist': None,
        'confidence': 'insufficient',
        'basis': 'unavailable',
        'scope': 'Softcore / Non-Ladder / PC / Reign of the Warlock',
        'dates': summary['observed_dates'],
        'sellers': summary['priced_sellers'],
        'notes': ['Asks are not confirmed sale prices.'],
        'excluded_observations': excluded,
        'publication_policy': {
            'minimum_sellers': MIN_SELLERS,
            'maximum_age_days': MAX_AGE_DAYS,
            'maximum_dispersion': MAX_DISPERSION,
            'as_of': today.isoformat(),
        },
    }
    if not comparables['contract']:
        result['unavailable_reason'] = 'unclassified'
        return result
    if 0 < summary['priced_sellers'] < MIN_SELLERS:
        result['comparable_asks'] = independent_asks(eligible)
    blockers = []
    if summary['priced_sellers'] < MIN_SELLERS:
        result['unavailable_reason'] = 'thin' if summary['priced_sellers'] else 'no_matches'
        blockers.append(f'Need {MIN_SELLERS} independent comparable sellers; found {summary["priced_sellers"]}.')
        if excluded.get('stale') or excluded.get('future'):
            result['unavailable_reason'] = 'stale'
            blockers.append('Too few sellers inside the publication date window.')
        elif excluded.get('undated'):
            result['unavailable_reason'] = 'undated'
            blockers.append('Too few sellers with verified observation dates.')
    if summary['min_ist'] and summary['max_ist'] / summary['min_ist'] > MAX_DISPERSION:
        result['unavailable_reason'] = 'dispersed'
        blockers.append('Comparable asks are too dispersed for a single estimate.')
    if blockers:
        result['notes'].extend(dict.fromkeys(blockers))
        result['notes'].append('Missing evidence does not mean worthless.')
    else:
        result.update(
            estimate_ist=summary['median_ist'],
            low_ist=summary['min_ist'],
            high_ist=summary['max_ist'],
            confidence='low',
            basis='classified_exact_variant_asks',
            comparables=summary['representatives'],
        )
        result['notes'].append('Matches declared listing modifiers; omitted listing stats may still differ.')
    # Full listings remain in classifier diagnostics, including thin/historical cohorts.
    return result
