"""Recover reviewed collection dates without re-materializing unrelated market facets."""

import argparse
import copy
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market import import_cache
from pricing.knowledge.refresh import atomic_json


DATE_FIELDS = frozenset(
    {'id', 'observed_at', 'observation_date_basis', 'observation_date_precision', 'observation_date_source'}
)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _key(row):
    return row.get('source'), row.get('listing_id'), row.get('listing_updated_at')


def _material(row, generation, *, fresh):
    result = copy.deepcopy({k: v for k, v in row.items() if k not in DATE_FIELDS})
    base = result.get('facet_basis', {}).get('base_code', {})
    if base.get('kind') == 'named_definition' and base.get('path') == 'pricing/data/appraisal-definitions.json':
        origin = base.get('generation')
        if not isinstance(origin, str) or not re.fullmatch('[0-9a-f]{64}', origin) or (fresh and origin != generation):
            raise ValueError('Unverified definition generation in recovered observation')
        # Preserve the historical derivation, after current normalization proves
        # all actual fields and the other provenance semantics unchanged.
        del base['generation']
    return result


def recover_rows(existing, normalized, definition_generation):
    indexed = defaultdict(list)
    for index, row in enumerate(existing):
        indexed[_key(row)].append(index)
    output, changes, seen = list(existing), [], set()
    for fresh in normalized:
        if fresh.get('observation_date_basis') != 'documented_collection':
            continue
        key = _key(fresh)
        indices = indexed.get(key, ())
        if key in seen or len(indices) != 1:
            raise ValueError('Recovered collection does not identify one existing observation')
        seen.add(key)
        index = indices[0]
        old = existing[index]
        if old.get('observed_at') not in (None, fresh['observed_at']):
            raise ValueError('Conflicting existing observation date')
        if _material(old, definition_generation, fresh=False) != _material(fresh, definition_generation, fresh=True):
            raise ValueError('Date recovery changes non-date evidence')
        updated = {k: v for k, v in old.items() if k not in DATE_FIELDS}
        updated.update({k: fresh[k] for k in DATE_FIELDS if k in fresh})
        if updated == old:
            continue
        output[index] = updated
        changes.append(
            {
                'source': old['source'],
                'listing_id': old['listing_id'],
                'old_id': old['id'],
                'new_id': updated['id'],
                'old_sha256': fingerprint(old),
                'new_sha256': fingerprint(updated),
                'verified_normalization_sha256': fingerprint(fresh),
                'definition_generation': definition_generation,
            }
        )
    if len({r['id'] for r in output}) != len(output):
        raise ValueError('Recovered dates collide with existing observation identities')
    return output, changes


def verify_policy_sources(rows, document):
    indexed = {r['id']: r for r in rows}
    for policy in document['policies']:
        for owner in (policy, *policy.get('variant_rules', [])):
            for evidence in owner.get('trade_qualification', {}).get('market_evidence', ()):
                row = indexed.get(evidence['id'])
                # Reviews retain either a digest or the complete normalized row.
                # An unhashed subset is not evidence of unchanged omitted fields.
                expected = (
                    evidence['normalized_row_sha256'] if 'normalized_row_sha256' in evidence else fingerprint(evidence)
                )
                if row is None or fingerprint(row) != expected:
                    raise ValueError(f'Date recovery invalidates reviewed trade evidence: {policy["name"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Apply the validated date-only reconciliation offline')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    data = root / 'pricing/data'
    path = data / 'appraisal-market.jsonl'
    market_raw = path.read_bytes()
    existing = [json.loads(line) for line in market_raw.splitlines()]
    manifest_path = data / 'appraisal-market-manifest.json'
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    items = json.loads((data / 'appraisal-traderie-catalog.json').read_text())['items']
    normalized, imported = import_cache(root, items)
    if errors := [f for f in imported['files'] if f.get('observation_date_error')]:
        raise ValueError(f'Collection-date validation failed: {errors}')
    output, changes = recover_rows(existing, normalized, catalog().generation)
    policies = json.loads((root / 'pricing/knowledge/assessment/rules/named_tiers.json').read_text())
    verify_policy_sources(output, policies)
    proof = {
        'schema_version': 1,
        'observations': len(output),
        'changed': len(changes),
        'dated_before': sum(bool(r.get('observed_at')) for r in existing),
        'dated_after': sum(bool(r.get('observed_at')) for r in output),
        'changes': changes,
    }
    files = {f['path']: f for f in imported['files']}
    for i, original in enumerate(manifest['files']):
        fresh = files.get(original['path'], {})
        if fresh.get('observation_date_source'):
            if original['sha256'] != fresh['sha256'] or original['listing_count'] != fresh['listing_count']:
                raise ValueError('Published cache manifest differs from date recovery')
            manifest['files'][i] = fresh
    if args.write:
        if path.read_bytes() != market_raw or manifest_path.read_bytes() != manifest_raw:
            raise ValueError('Market evidence changed during date recovery')
        # The selected runtime remains unchanged until the rebuilt index is published.
        temporary = path.with_suffix('.jsonl.tmp')
        temporary.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in output))
        temporary.replace(path)
        atomic_json(manifest_path, manifest)
        if changes:
            atomic_json(data / 'appraisal-collection-date-recovery.json', proof)
    print(json.dumps({k: v for k, v in proof.items() if k != 'changes'}))


if __name__ == '__main__':
    main()
