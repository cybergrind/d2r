"""Resolve reviewed seasonal scalar differences from complete item captures."""

from pricing.knowledge.seasonal_variants import select_scalar_candidates


def select_seasonal(candidates, facts):
    # Socket payloads can add the same discriminator; do not attribute their
    # contribution to the native unique. Partial captures cannot prove absence.
    if (
        len(candidates) != 2
        or not any(c.get('ordinary_definition') or c.get('ladder_definition') for c in candidates)
        or facts.gaps
        or not facts.capture_complete
        or facts.identified is not True
        or facts.sockets != 0
        or facts.socket_contents != 'empty'
    ):
        return candidates
    return select_scalar_candidates(candidates, facts.stats)


def non_ladder_capture_gap(definition, facts):
    """Reject recognized off-mode bonuses without guessing from partial/socketed stats."""
    if not (ladder := definition.get('ladder_definition')):
        return None
    selected = select_seasonal([definition, ladder], facts)
    if selected == [ladder]:
        return 'Captured modifiers match a Ladder-only version, outside Non-Ladder scope.'
    if not selected:
        return 'Captured modifiers conflict with the reviewed ordinary and Ladder versions.'
    return None


def _comparison_variants(definition, facts):
    from pricing.knowledge.definition_store import catalog

    variants = [
        v
        for v in catalog().named_variants.get((facts.rarity, facts.name), ())
        if v.get('table_id') == definition.get('table_id')
    ]
    variants.extend(v['ladder_definition'] for v in tuple(variants) if v.get('ladder_definition'))
    return variants


def shared_scalar_ranges(definition, facts):
    """Only shared constants may be supplied when a listing omits them."""
    ranges = definition.get('roll_ranges', {})
    variants = _comparison_variants(definition, facts)
    if not any(v.get('ordinary_definition') or v.get('ladder_definition') for v in variants):
        return ranges
    return {
        key: value for key, value in ranges.items() if all(v.get('roll_ranges', {}).get(key) == value for v in variants)
    }


def comparison_discriminators(definition, facts):
    """Require explicit market evidence, including zero on the ordinary version."""
    from inventory_tracking.items.metadata import metadata

    variants = _comparison_variants(definition, facts)
    if len(variants) != 2 or not any(v.get('ordinary_definition') or v.get('ladder_definition') for v in variants):
        return {}
    left, right = [v.get('roll_ranges', {}) for v in variants]
    keys = {k for k in {'105', '93', '96'} if left.get(k) != right.get(k)}
    return {metadata()['stats'][key]['property_id']: facts.stats.get(key + ':0', {}).get('value', 0) for key in keys}
