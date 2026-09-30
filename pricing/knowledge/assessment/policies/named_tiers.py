"""Strict specimen-tier refinements; reports compose these with named_baselines."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import named_definitions, resolve_named_definition
from pricing.knowledge.assessment.handlers.random_skills import comparison_gaps
from pricing.knowledge.assessment.mechanics.intrinsic_socket_rolls import SUPPORTED, intrinsic_socket_rolls
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.assessment.roles.predicates import Truth, evaluate, native_keys, validate
from pricing.knowledge.definition_store import catalog


RULES = Path(__file__).resolve().parents[1] / 'rules/named_tiers.json'
ROOT = Path(__file__).resolve().parents[4]
TIERS = frozenset({'high', 'med', 'low', 'trash'})


@lru_cache(maxsize=2)
def _policies(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported named tier schema')
    result = {}
    for policy in document['policies']:
        key = (policy['quality'], policy['name'])
        if key in result or key not in named_definitions():
            raise ValueError('Duplicate or unknown named tier identity')
        if policy['default_tier'] not in TIERS or not policy.get('review') or not policy['source'].get('locator'):
            raise ValueError('Invalid/unreviewed named tier policy')
        if policy.get('basis_kind') not in (None, 'qualitative'):
            raise ValueError('Invalid named tier evidence kind')
        validate(policy['valid_if'])
        socket_keys = policy.get('intrinsic_socket_stats', [])
        if not isinstance(socket_keys, list) or any(
            not isinstance(key, str) or key not in SUPPORTED for key in socket_keys
        ):
            raise ValueError('Unsupported intrinsic socket roll policy')
        for override in policy['overrides']:
            if override['tier'] not in TIERS:
                raise ValueError('Invalid named tier override')
            validate(override['when'])
        variants = policy.get('variant_rules', [])
        known_ids = {v['table_id'] for v in catalog().named_variants[key]}
        seen_ids = set()
        for variant in variants:
            ids = variant['table_ids']
            if (
                not ids
                or any(type(i) is not int or i not in known_ids or i in seen_ids for i in ids)
                or len(set(ids)) != len(ids)
                or variant['default_tier'] not in TIERS
            ):
                raise ValueError('Invalid named tier definition variant')
            seen_ids.update(ids)
            validate(variant['valid_if'])
            for override in variant['overrides']:
                if override['tier'] not in TIERS:
                    raise ValueError('Invalid variant tier override')
                validate(override['when'])
        if variants and (seen_ids != known_ids or socket_keys):
            raise ValueError('Variant tiers must cover the native records and cannot mix intrinsic socket rules')
        if socket_keys:
            required = set(native_keys(policy['valid_if']))
            for override in policy['overrides']:
                required.update(native_keys(override['when']))
            if not required.issubset(socket_keys):
                raise ValueError('Socket policy must adjust every tier-dependent stat')
        result[key] = policy
    return result


def assess_tier(facts):
    pending = {'status': 'pending_review', 'tier': None, 'possible_tiers': []}
    if facts.rarity not in ('unique', 'set') or facts.identified is not True:
        return pending
    try:
        policy = _policies(read_artifact(RULES)).get((facts.rarity, facts.name))
    except OSError, ValueError, KeyError, TypeError:
        return pending
    if not policy:
        return pending
    error = source_error(policy['source'], (facts.rarity, facts.name), ROOT)
    if error:
        return {**pending, 'source_error': error}
    definition, _ = resolve_named_definition(facts, identity_only=True)
    if definition is None or comparison_gaps(facts, definition, require_projection=False):
        return pending
    if policy.get('variant_rules'):
        variant = next(v for v in policy['variant_rules'] if definition['table_id'] in v['table_ids'])
        policy = {
            **policy,
            'default_tier': variant['default_tier'],
            'valid_if': {'all': [policy['valid_if'], variant['valid_if']]},
            'overrides': variant['overrides'],
        }
    intrinsic = {}
    if policy.get('intrinsic_socket_stats'):
        facts, intrinsic = intrinsic_socket_rolls(facts, policy['intrinsic_socket_stats'])
        if facts is None:
            return pending
    validity = evaluate(policy['valid_if'], facts)
    if validity.truth == Truth.FALSE:
        return pending
    possible = []
    reasons = []
    for rule in policy['overrides']:
        outcome = evaluate(rule['when'], facts)
        if outcome.truth != Truth.FALSE:
            possible.append(rule['tier'])
            reasons.append(rule['reason'])
        if outcome.truth == Truth.TRUE:
            break
    else:
        possible.append(policy['default_tier'])
    possible = list(dict.fromkeys(possible))
    resolved = validity.truth == Truth.TRUE and len(possible) == 1
    return {
        'status': 'reviewed' if resolved else 'conditional',
        'tier': possible[0] if resolved else None,
        'possible_tiers': possible,
        'reasons': reasons,
        'source': dict(policy['source']),
        'basis': policy['review'],
        **({'basis_kind': policy['basis_kind']} if policy.get('basis_kind') else {}),
        **({'intrinsic_rolls': intrinsic} if intrinsic else {}),
        **(
            {
                'intrinsic_roll_ranges': {
                    key: dict(definition['roll_ranges'].get(key, definition['roll_ranges'].get(key.split(':')[0], {})))
                    for key in intrinsic
                }
            }
            if intrinsic
            else {}
        ),
    }
