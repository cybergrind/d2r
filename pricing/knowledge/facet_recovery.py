"""Reconcile verified facet identities without replacing unrelated market evidence."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from pricing.knowledge.date_recovery import fingerprint, verify_policy_sources
from pricing.knowledge.market import normalize_facets, property_values
from pricing.knowledge.market_facet_catalog import VARIANTS
from pricing.knowledge.refresh import atomic_json


DERIVED_FIELDS = frozenset(
    {
        'name',
        'catalog_name',
        'rarity',
        'sockets',
        'ethereal',
        'rarity_basis',
        'base_code',
        'base_upgrade',
        'base_rarity',
        'base_selector_properties',
        'socket_contents',
        'socket_contents_basis',
        'facet_basis',
        'mechanics_conflicts',
    }
)


def preserved(row):
    return {key: value for key, value in row.items() if key not in DERIVED_FIELDS}


def reconcile_facets(rows):
    labels = {identity: 'Rainbow Facet: ' + label for _, identity, label, *_ in VARIANTS}
    output, changes = [], []
    for original in rows:
        label = labels.get(original.get('catalog_id'))
        named = original.get('name') == label or (
            original.get('name') == 'Rainbow Facet' and original.get('catalog_name') == label
        )
        if not label or not named or original.get('category') not in ('unique', 'uniques'):
            output.append(original)
            continue
        if original.get('properties') != property_values(original.get('raw_properties', [])):
            raise ValueError('Facet properties differ from the raw listing')
        updated = copy.deepcopy(original)
        normalize_facets(updated)
        if updated.get('name') != 'Rainbow Facet' or updated.get('catalog_name') != label:
            raise ValueError('Facet native identity could not be verified')
        if preserved(original) != preserved(updated):
            raise ValueError('Facet recovery changed non-derived market evidence')
        output.append(updated)
        if updated != original:
            changes.append(
                {
                    'id': original['id'],
                    'catalog_id': original['catalog_id'],
                    'before': fingerprint(original),
                    'after': fingerprint(updated),
                    'fields': sorted(
                        key for key in original.keys() | updated.keys() if original.get(key) != updated.get(key)
                    ),
                    'conflicts': updated.get('mechanics_conflicts', []),
                }
            )
    return output, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    path = root / 'pricing/data/appraisal-market.jsonl'
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    output, changes = reconcile_facets(rows)
    verify_policy_sources(
        output, json.loads((root / 'pricing/knowledge/assessment/rules/named_tiers.json').read_bytes())
    )
    proof = {
        'schema_version': 1,
        'observations': len(rows),
        'changed': len(changes),
        'unchanged': len(rows) - len(changes),
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'existing_trade_evidence_preserved': True,
        'changes': changes,
    }
    if args.write and changes:
        if path.read_bytes() != raw:
            raise ValueError('Market evidence changed during facet reconciliation')
        temporary = path.with_suffix('.jsonl.tmp')
        temporary.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in output))
        temporary.replace(path)
        atomic_json(root / 'pricing/data/appraisal-facet-recovery.json', proof)
    print(json.dumps({key: value for key, value in proof.items() if key != 'changes'}))


if __name__ == '__main__':
    main()
