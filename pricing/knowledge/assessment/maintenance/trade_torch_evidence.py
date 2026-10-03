"""Scoped class census for Torch trade reviews; thin classes remain unknown."""

import hashlib
import json
from collections import Counter
from datetime import date
from math import isfinite

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.policies.trade_class_skills import IDENTITY, market_class, specification
from pricing.knowledge.assessment.property_equivalence import ATTRIBUTES, ELEMENTAL_RESISTANCES, canonical_properties
from pricing.knowledge.date_recovery import fingerprint
from pricing.knowledge.market import scope_status


MARKET = 'pricing/data/appraisal-market.jsonl'
ALL_CLASSES = {'class_skill_ids': list(range(8))}


def audit(observations):
    definition, _, properties = specification(ALL_CLASSES)
    groups = {i: [] for i in range(8)}
    excluded = Counter()
    for row in observations:
        if (row.get('rarity'), row.get('name')) != IDENTITY:
            continue
        props = row.get('properties', {})
        if row.get('scope_status') != 'verified' or scope_status(props) != 'verified':
            excluded['scope'] += 1
            continue
        if (
            row.get('base_code') not in definition['base_codes']
            or row.get('ethereal') is not False
            or type(row.get('sockets')) is not int
            or row['sockets'] != 0
            or row.get('socket_contents') != 'empty'
            or row.get('mechanics_conflicts')
        ):
            excluded['variant'] += 1
            continue
        if (
            row.get('evidence_kind') != 'ask'
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
        ):
            excluded['ask_unit'] += 1
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
            class_id = market_class(ALL_CLASSES, row)
            canonical = canonical_properties(props)
        except KeyError, TypeError, ValueError:
            excluded['date_class_or_properties'] += 1
            continue
        rolls = []
        for members in (ATTRIBUTES, ELEMENTAL_RESISTANCES):
            values = [canonical.get(k) for k in members]
            if (
                not all(type(v) in (int, float) and 10 <= v <= 20 and v == int(v) for v in values)
                or len(set(values)) != 1
            ):
                break
            rolls.append(int(values[0]))
        if len(rolls) != 2:
            excluded['compound_rolls'] += 1
            continue
        ask = row.get('ask_ist')
        if type(ask) not in (int, float) or not isfinite(ask) or ask <= 0 or not row.get('seller_id'):
            excluded['priced_seller'] += 1
            continue
        groups[class_id].append(
            {'id': row['id'], 'seller_id': row['seller_id'], 'rolls': rolls, 'normalized_row_sha256': fingerprint(row)}
        )
    return {
        'classes': [
            {
                'class_id': i,
                'class_name': CLASS_NAMES[i],
                'property': properties[i],
                'priced_sellers': sorted({r['seller_id'] for r in groups[i]}),
                'rows': sorted(groups[i], key=lambda r: r['id']),
            }
            for i in range(8)
        ],
        'excluded': dict(sorted(excluded.items())),
    }


def reviewed_classes(evidence, allowed):
    rows = evidence.get('classes', [])
    if [row.get('class_id') for row in rows] != list(range(8)):
        return False
    for row in rows:
        sellers = row.get('priced_sellers')
        if (
            not isinstance(sellers, list)
            or any(not isinstance(s, str) or not s for s in sellers)
            or len(sellers) != len(set(sellers))
            or (len(sellers) >= 3) != (row['class_id'] in allowed)
        ):
            return False
    return True


def load_evidence(root, document, policies, scopes):
    if not any(r['scope'] in scopes and (r['quality'], r['name']) == IDENTITY for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    if policies.get(IDENTITY, {}).get('trade_qualification', {}).get('market_snapshot') != snapshot:
        return {}
    return {IDENTITY: {**audit(json.loads(line) for line in raw.splitlines()), 'market_snapshot': snapshot}}
