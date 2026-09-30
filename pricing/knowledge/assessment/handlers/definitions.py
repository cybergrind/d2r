"""Shared offline definition lookup for named identities and recipes."""

from pricing.knowledge.assessment.mechanics.base_tiers import is_base_upgrade
from pricing.knowledge.definition_store import catalog


def named_definitions():
    return catalog().named


def resolve_named_definition(facts, *, identity_only=False):
    """Resolve the captured table record without collapsing same-name variants."""
    from collections.abc import Mapping

    variants = catalog().named_variants.get((facts.rarity, facts.name), ())
    if not variants:
        return None, ['Named identity is absent from the offline definitions.']
    capture = facts.provenance.get('capture', {})
    if 'item_identity' in capture:
        identity = capture['item_identity']
        if (
            not isinstance(identity, Mapping)
            or identity.get('table') != facts.rarity
            or type(identity.get('table_id')) is not int
        ):
            return None, ['Captured named table identity is invalid or conflicting.']
        variants = [v for v in variants if v.get('table_id') == identity['table_id']]
        if not variants:
            return None, ['Captured named table identity conflicts with the item name.']
        if not identity_only and identity.get('mode_eligibility') == 'ladder_only':
            return None, ['Captured item is a recognized Ladder-only version, outside Non-Ladder scope.']
    candidates = [v for v in variants if facts.base_code in v.get('base_codes', ())]
    if not candidates and facts.rarity in {'unique', 'set'} and 'item_identity' in capture:
        candidates = [
            v for v in variants if any(is_base_upgrade(code, facts.base_code) for code in v.get('base_codes', ()))
        ]
    if not candidates:
        return None, ['Named item base or upgrade is not verified by its definition.']
    if len(candidates) > 1:
        from pricing.knowledge.assessment.handlers.seasonal import select_seasonal

        candidates = select_seasonal(candidates, facts)
    if (
        identity_only
        and len(candidates) == 2
        and candidates[0].get('table_id') == candidates[1].get('table_id')
        and any(candidate.get('ordinary_definition') for candidate in candidates)
    ):
        return _shared_fields(*candidates), []
    if len(candidates) != 1:
        return None, ['Named variant is ambiguous; a verified table identity is required.']
    if not identity_only:
        from pricing.knowledge.assessment.handlers.seasonal import non_ladder_capture_gap

        if gap := non_ladder_capture_gap(candidates[0], facts):
            return None, [gap]
    return candidates[0], []


def _shared_fields(left, right):
    """Identity-only policies may use facts shared by both definition versions.

    Exact comparison and roll consumers must continue resolving one version.
    In particular, differing requirements and stat ranges are not inherited.
    """
    from collections.abc import Mapping

    shared = {}
    for key in left.keys() & right.keys():
        a, b = left[key], right[key]
        if a == b:
            shared[key] = a
        elif isinstance(a, Mapping) and isinstance(b, Mapping):
            shared[key] = _shared_fields(a, b)
    return shared
