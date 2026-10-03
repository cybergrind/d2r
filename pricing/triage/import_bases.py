"""Transcribe clean WP-B bucket definitions; rebuild prices from scoped listings."""

import json
import re
from collections import Counter

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'pricing/data/wp-b-prices.json'


def compile_bucket(name, key):
    parts = key.split('/')
    if len(parts) < 3 or not re.fullmatch(r'[0-6]os', parts[0]):
        return None
    sockets, ethereal, rarity, *suffixes = parts
    if ethereal not in ('eth', 'noneth') or rarity not in ('normal', 'superior'):
        return None
    if set(suffixes) - {'15ed', 'res45', 'res40-44', 'res<40', 'skill1', 'skill2', 'skill3'}:
        return None
    conditions = {
        'sockets': int(sockets[0]),
        'ethereal': ethereal == 'eth',
        'rarity': rarity,
        'empty_sockets': True,
        'base_ed': 15 if '15ed' in suffixes else {'min': 0, 'max': 14},
    }
    properties = {}
    for suffix in suffixes:
        if suffix.startswith('res'):
            properties['441'] = {'res45': 45, 'res40-44': {'min': 40, 'max': 44}, 'res<40': {'min': 0, 'max': 39}}[
                suffix
            ]
        elif suffix.startswith('skill'):
            properties['454'] = int(suffix[-1])
    return {
        'category': 'base',
        'name': name,
        'bucket': 'wp-b:' + key,
        'conditions': conditions,
        'properties': properties,
        'source': SOURCE + '#' + name + '/' + key,
    }


def main():
    source = json.loads((ROOT / SOURCE).read_text())
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows, skipped = [], Counter()
    for entry in source.values():
        if not isinstance(entry, dict) or 'buckets' not in entry:
            continue
        for key in entry['buckets']:
            rule = compile_bucket(entry['name'], key)
            if rule:
                rows.append(rule)
            else:
                skipped[key] += 1
    document['rows'] = [
        r for r in document['rows'] if not (isinstance(r.get('source'), str) and r['source'].startswith(SOURCE + '#'))
    ] + rows
    policy = next(p for p in document['policies'] if p.get('category') == 'base' and 'name' not in p)
    policy['require_bucket'] = True
    atomic_json(path, document)
    print(
        json.dumps(
            {
                'rules': len(rows),
                'bases': len({r['name'] for r in rows}),
                'skipped_buckets': sum(skipped.values()),
                'historical_prices_imported': False,
            }
        )
    )


if __name__ == '__main__':
    main()
