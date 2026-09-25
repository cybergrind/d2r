"""Durable offline review ledger from saved-item replay results, never a valuation."""

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.refresh import atomic_json


def review_gaps(assessment, price):
    facts = assessment['facts']
    gaps = []
    for dimension, reasons in (
        ('capture', facts.get('gaps', [])),
        ('market_mapping', facts.get('projection_gaps', [])),
        ('desirability', assessment.get('coverage_gaps', [])),
    ):
        gaps.extend({'dimension': dimension, 'state': 'pending', 'reason': reason} for reason in sorted(set(reasons)))
    if price.get('estimate_ist') is None:
        gaps.append(
            {
                'dimension': 'market',
                'state': 'pending',
                'reason': price.get('unavailable_reason') or 'No estimate supplied',
            }
        )
    return gaps


def merge_replays(previous, replays, capture_hashes):
    records = {r['id']: deepcopy(r) for r in previous.get('captures', [])}
    if len(records) != len(previous.get('captures', [])):
        raise ValueError('Duplicate capture review identity')
    for replay in replays.values():
        source = replay['source']
        digest = capture_hashes[source]
        capture_id = fingerprint({'source': source, 'sha256': digest})
        assessment, price = replay['assessment'], replay['price_estimate']
        revision = {
            'id': fingerprint({'assessment': assessment, 'price_estimate': price}),
            'assessment': deepcopy(assessment),
            'price_estimate': deepcopy(price),
            'gaps': review_gaps(assessment, price),
        }
        record = records.setdefault(
            capture_id,
            {
                'id': capture_id,
                'source': source,
                'capture_sha256': digest,
                'history': [],
            },
        )
        if not any(r['id'] == revision['id'] for r in record['history']):
            record['history'].append(revision)
        record['latest_revision'] = revision['id']
        record['facts'] = deepcopy(assessment['facts'])
        record['gaps'] = revision['gaps']
    return {'schema_version': 1, 'complete': False, 'captures': [records[k] for k in sorted(records)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('replay', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'pricing/data/appraisal-observed-review.json')
    args = parser.parse_args()
    replays = json.loads(args.replay.read_text())
    hashes = {}
    for replay in replays.values():
        path = (ROOT / replay['source']).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Replay source must be a local saved capture')
        hashes[replay['source']] = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = json.loads(args.output.read_text()) if args.output.exists() else {}
    result = merge_replays(previous, replays, hashes)
    atomic_json(args.output, result)
    print(
        json.dumps({'captures': len(result['captures']), 'open_gaps': sum(len(r['gaps']) for r in result['captures'])})
    )


if __name__ == '__main__':
    main()
