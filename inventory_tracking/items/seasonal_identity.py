"""Keep ordinary named-item ranges when seasonal overlays reuse their ID."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.seasonal_variants import select_scalar_candidates


def resolve_seasonal_identity(entry, arrays, *, socketed):
    if ladder := entry.get('ladder_definition'):
        stats = scalar_capture(arrays) if arrays.get('complete') is True and not socketed else None
        if stats is not None:
            matches = select_scalar_candidates([entry, ladder], stats)
            if matches == [ladder]:
                return {**ladder, 'definition_variant': 'seasonal', 'mode_eligibility': 'ladder_only'}
            if not matches:
                return _unresolved(entry, ladder)
        # The configured mode establishes the default; this does not claim that
        # an incomplete capture proved an absent stat or identified another mode.
        return {**entry, 'definition_variant': 'ordinary', 'variant_basis': 'non_ladder_scope'}
    ordinary = entry.get('ordinary_definition')
    if ordinary is None:
        return entry
    candidates = [ordinary, entry]
    stats = scalar_capture(arrays) if arrays.get('complete') is True and not socketed else None
    if stats is not None:
        matches = select_scalar_candidates(candidates, stats)
        if len(matches) == 1:
            selected = matches[0]
            return {**selected, 'definition_variant': 'ordinary' if selected is ordinary else 'seasonal'}
    return _unresolved(entry, ordinary)


def _unresolved(entry, ordinary):
    """Preserve identity and shared annotations; never borrow a removed range."""
    return {
        **entry,
        'definition_variant': 'unresolved',
        'roll_ranges': {k: v for k, v in entry['roll_ranges'].items() if ordinary['roll_ranges'].get(k) == v},
        'enhanced_damage_expected': entry['enhanced_damage_expected'] and ordinary['enhanced_damage_expected'],
        'base_defense_range': (
            entry.get('base_defense_range')
            if entry.get('base_defense_range') == ordinary.get('base_defense_range')
            else None
        ),
    }


def scalar_capture(arrays):
    """Only structurally valid totals can prove a discriminator is absent."""
    descriptors = arrays.get('arrays')
    if not isinstance(descriptors, list) or any(not isinstance(row, dict) for row in descriptors):
        return None
    totals = [row for row in descriptors if row.get('header_offset') == 0xE8]
    if len(totals) != 1 or not isinstance(totals[0].get('stats'), list):
        return None
    stats = {}
    for stat in totals[0]['stats']:
        if not isinstance(stat, dict) or any(type(stat.get(key)) is not int for key in ('id', 'layer', 'raw')):
            return None
        if stat['id'] not in (93, 96, 105, 107):
            continue
        key = str(stat['id']) + ':' + str(stat['layer'])
        if (stat['id'] != 107 and stat['layer'] != 0) or key in stats:
            return None
        shift = metadata()['stats'][str(stat['id'])]['shift']
        stats[key] = {'status': 'decoded', 'value': stat['raw'] / (1 << shift)}
    return stats
