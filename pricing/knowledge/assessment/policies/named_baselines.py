"""Identity baselines composed with independently validated specimen tiers.

The conditional rules in named_tiers assess a particular specimen. Failure to
match those rules cannot erase the reviewed value of the underlying identity.
Neither layer creates or relaxes an exact-price contract.
"""

import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.named_variant_legality import impossible_named_variant
from pricing.knowledge.assessment.policies import named_tiers
from pricing.knowledge.assessment.policies.complete_sets import assess_complete_set
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.definition_store import catalog


RULES = named_tiers.RULES.parent / 'named_baselines.json'
ROOT = named_tiers.ROOT


@lru_cache(maxsize=2)
def baselines(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported named baseline schema')
    result = {}
    for row in document['rows']:
        identity = row['quality'], row['name']
        if identity in result or identity not in catalog().named:
            raise ValueError('Duplicate or unknown named baseline identity')
        if row['tier'] not in named_tiers.TIERS or not row.get('basis') or not row.get('reviewed_at'):
            raise ValueError('Invalid or unreviewed named baseline')
        if not row['source'].get('locator'):
            raise ValueError('Missing named baseline evidence')
        result[identity] = row
    return result


def assess_tier(facts):
    pending = {'status': 'pending_review', 'tier': None, 'possible_tiers': []}
    if facts.rarity not in ('unique', 'set') or facts.identified is not True:
        return pending
    if facts.rarity == 'set' and facts.ethereal is True:
        return pending
    definition, _ = resolve_named_definition(facts, identity_only=True)
    if definition is None or impossible_named_variant(facts, definition):
        return pending
    identity = facts.rarity, facts.name
    try:
        row = baselines(read_artifact(RULES)).get(identity)
    except OSError, ValueError, KeyError, TypeError:
        return pending
    if row is None:
        return pending
    error = source_error(row['source'], identity, ROOT)
    if error:
        return {**pending, 'source_error': error}
    baseline = {
        'status': 'reviewed',
        'tier': row['tier'],
        'possible_tiers': [row['tier']],
        'source': dict(row['source']),
        'basis': row['basis'],
        'basis_kind': 'qualitative',
        'reviewed_at': row['reviewed_at'],
    }
    variant = named_tiers.assess_tier(facts)
    selected = variant if variant.get('tier') is not None else baseline
    result = {**selected, 'baseline': baseline, 'variant': variant}
    for key in ('intrinsic_rolls', 'intrinsic_roll_ranges'):
        if key in variant:
            result[key] = variant[key]
    if facts.rarity == 'set':
        result['set_context'] = assess_complete_set(definition['game_definition']['set'])
    return result
