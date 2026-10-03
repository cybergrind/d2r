"""Reviewed trade candidates, independent of gear fit and numerical estimates."""

from datetime import date

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.facet import facet_trigger
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.assessment.policies.trade_barter import validate_barter
from pricing.knowledge.assessment.policies.trade_base_defense import valid_base_defense
from pricing.knowledge.assessment.policies.trade_choices import valid_reviewed_choice
from pricing.knowledge.assessment.policies.trade_class_skills import valid_capture as valid_class_capture
from pricing.knowledge.assessment.policies.trade_evidence import validate_segments
from pricing.knowledge.assessment.policies.trade_facets import valid_rolls
from pricing.knowledge.assessment.policies.trade_rolls import valid_compounds
from pricing.knowledge.assessment.roles.predicates import Truth, evaluate, native_keys, validate
from pricing.knowledge.market import scope_status


SCOPE = 'SC / Non-Ladder / PC / RotW'
STATUSES = {'candidate', 'premium', 'use_only'}


def validate_review(review, identity, parent_valid_if):
    """Validate explicit review rules; no inference from a tier or build count."""
    if review.get('scope') != SCOPE or review.get('basis') != 'reviewed_asking_segments':
        raise ValueError('Invalid trade qualification scope or basis')
    date.fromisoformat(review['reviewed_at'])
    if review.get('default_status') not in STATUSES | {'unresolved'} or not review.get('default_reason'):
        raise ValueError('Missing trade qualification disposition')
    validate(review['valid_if'])
    keys = set(native_keys(review['valid_if']))
    for band in review['bands']:
        if band.get('status') not in STATUSES or not band.get('reason'):
            raise ValueError('Invalid trade qualification band')
        validate(band['when'])
        keys.update(native_keys(band['when']))
    if keys - set(review['material_stats']):
        raise ValueError('Unlisted material trade roll')
    evidence = review['market_evidence']
    barter_ids = validate_barter(review)
    seen = set()
    sellers = set()
    for row in evidence:
        props = row['properties']
        if (
            row['id'] in seen
            or (row.get('rarity'), row.get('name')) != identity
            or row.get('scope_status') != 'verified'
            or scope_status(props) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or not row.get('seller_id')
            or (
                row['id'] not in barter_ids
                and (type(row.get('ask_ist')) not in (int, float) or not 0 < row['ask_ist'] < float('inf'))
            )
        ):
            raise ValueError('Invalid scoped trade qualification evidence')
        date.fromisoformat(row['observed_at'][:10])
        seen.add(row['id'])
        sellers.add(row['seller_id'])
    if len(sellers) < 3:
        raise ValueError('Insufficient independent trade evidence')
    indexed = {row['id']: row for row in evidence}
    groups = [(review['default_status'], review['default_evidence_ids'])]
    groups.extend((band['status'], band['evidence_ids']) for band in review['bands'])
    for status, ids in groups:
        if status == 'unresolved' and not ids:
            continue  # No positive or negative trade claim; absence is not worthlessness.
        if not ids or len(ids) != len(set(ids)) or set(ids) - indexed.keys():
            raise ValueError('Invalid trade band evidence references')
        if len({indexed[key]['seller_id'] for key in ids}) < 3:
            raise ValueError('Insufficient independent trade band evidence')
    validate_segments(review, parent_valid_if)


def assess_trade_qualification(facts):
    if (facts.rarity, facts.name) == ('unique', 'Crown of Ages'):
        from pricing.knowledge.assessment.policies.crown_trade import assess

        return assess(facts)
    if facts.rarity == 'magic':
        from pricing.knowledge.assessment.policies.magic_trade import assess

        return assess(facts)
    if (facts.rarity, facts.name) == ('unique', 'Harlequin Crest'):
        from pricing.knowledge.assessment.policies.shako_trade import assess

        return assess(facts)
    if (facts.rarity, facts.name) == ('unique', 'Stormshield'):
        from pricing.knowledge.assessment.policies.stormshield_trade import assess

        return assess(facts)
    # Rules share the named policy snapshot, but qualification is an independent
    # outcome. A baseline/override tier never supplies a missing trade review.
    from pricing.knowledge.assessment.policies import named_tiers

    pending = {'status': 'unresolved', 'reason': 'Material rolls or item variant need verification.'}
    try:
        policy = named_tiers._policies(read_artifact(named_tiers.RULES)).get((facts.rarity, facts.name))
    except OSError, ValueError, KeyError, TypeError:
        return {}
    if not policy:
        return {}
    review = policy.get('trade_qualification')
    variant_reviews = any('trade_qualification' in variant for variant in policy.get('variant_rules', []))
    if not review and not variant_reviews:
        return {}
    if facts.identified is not True:
        return pending
    if source_error(policy['source'], (facts.rarity, facts.name), named_tiers.ROOT):
        return {**pending, 'reason': 'Trade qualification evidence requires review.'}
    definition, _ = resolve_named_definition(facts, identity_only=True)
    if definition is None:
        return pending
    parent_valid = policy['valid_if']
    if variant_reviews:
        variant = next((v for v in policy['variant_rules'] if definition['table_id'] in v['table_ids']), None)
        if variant is None or facet_trigger(facts, definition)[2]:
            return pending
        review = variant['trade_qualification']
        parent_valid = {'all': [parent_valid, variant['valid_if']]}
    valid = evaluate({'all': [parent_valid, review['valid_if']]}, facts)
    if (
        valid.truth != Truth.TRUE
        or not valid_class_capture(review, facts)
        or not valid_rolls(review, facts)
        or not valid_compounds(review, facts)
        or not valid_base_defense(review, facts)
        or not valid_reviewed_choice(review, facts)
    ):
        return {**pending, 'conditions': valid.to_dict()}
    status, reason = review['default_status'], review['default_reason']
    for band in review['bands']:
        truth = evaluate(band['when'], facts).truth
        if truth == Truth.UNKNOWN:
            return pending
        if truth == Truth.TRUE:
            status, reason = band['status'], band['reason']
            break
    return {
        'status': status,
        'reason': reason,
        'material_stats': list(review['material_stats']),
        'basis': review['basis'],
        'reviewed_at': review['reviewed_at'],
        'source': dict(policy['source']),
    }
