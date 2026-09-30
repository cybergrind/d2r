"""Complete-set utility, kept separate from the tier of a captured component."""

import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.policies.named_tiers import ROOT, RULES as NAMED_RULES, TIERS
from pricing.knowledge.assessment.policies.sources import resolve_pointer, source_document
from pricing.knowledge.definition_store import catalog


RULES = NAMED_RULES.parent / 'complete_sets.json'
NATIVE = ROOT / 'third-parties/d2data/json/sets.json'


@lru_cache(maxsize=2)
def _load(raw, native_raw):
    document = json.loads(raw)
    digest, native = source_document(native_raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported complete-set schema')
    result = {}
    seen = set()
    for row in document['rows']:
        key = row['native_id']
        if key in seen or key not in native or row['tier'] not in TIERS or not row.get('basis'):
            raise ValueError('Invalid or duplicate complete-set review')
        source = row['source']
        if source['sha256'] != digest or resolve_pointer(native, source['locator']) != native[key]:
            raise ValueError('Complete-set source changed')
        members = {
            d['name']
            for (quality, _), d in catalog().named.items()
            if quality == 'set' and d['game_definition']['set'] == key
        }
        if not members or set(row['pieces']) != members:
            raise ValueError('Complete-set membership mismatch')
        seen.add(key)
        for alias in {key, row['name']}:
            if alias in result:
                raise ValueError('Ambiguous complete-set alias')
            result[alias] = row
    if seen != native.keys():
        raise ValueError('Missing complete-set reviews')
    return result


def assess_complete_set(name):
    pending = {'status': 'pending_review', 'tier': None, 'ownership': 'not_evaluated'}
    try:
        row = _load(read_artifact(RULES), read_artifact(NATIVE)).get(name)
    except OSError, ValueError, KeyError, TypeError:
        return pending
    if row is None:
        return pending
    return {**row, 'status': 'reviewed', 'ownership': 'not_evaluated', 'basis_kind': 'qualitative'}
