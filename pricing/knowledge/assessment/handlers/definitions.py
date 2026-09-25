"""Shared offline definition lookup for named identities and recipes."""

from pricing.knowledge.assessment.mechanics.base_tiers import is_base_upgrade
from pricing.knowledge.definition_store import catalog


def named_definitions():
    return catalog().named


def resolve_named_definition(facts):
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
    candidates = [v for v in variants if facts.base_code in v.get('base_codes', ())]
    if not candidates and facts.rarity in {'unique', 'set'} and 'item_identity' in capture:
        candidates = [
            v for v in variants if any(is_base_upgrade(code, facts.base_code) for code in v.get('base_codes', ()))
        ]
    if not candidates:
        return None, ['Named item base or upgrade is not verified by its definition.']
    if len(candidates) != 1:
        return None, ['Named variant is ambiguous; a verified table identity is required.']
    return candidates[0], []
