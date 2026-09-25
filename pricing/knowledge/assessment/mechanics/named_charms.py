"""Roll integrity for reviewed unique charms without socket/base contributions."""

import math

from pricing.knowledge.market_named_aliases import ORIGINAL_SUNDERS


# These original definitions have standalone scalar bonuses. Renewed charms
# have additional recipe/affix contributions and need their own proof.
STANDALONE_CHARMS = frozenset(ORIGINAL_SUNDERS.values()) | {
    'Annihilus',
    'Hellfire Torch',
    "Gheed's Fortune",
}
SHARED_ROLLS = {'all-stats': {0, 1, 2, 3}, 'res-all': {39, 41, 43, 45}}


def is_standalone_charm(facts):
    return facts.rarity == 'unique' and facts.name in STANDALONE_CHARMS


def shared_roll_gaps(facts, definition):
    if not is_standalone_charm(facts):
        return []
    gaps = []
    # Local properties.json: func1=1 rolls once; subsequent func3 entries reuse
    # nValue (D2MOO ItemMods.cpp ITEMMODS_PropertyFunc03). These are not four
    # independently rolled attributes/resistances.
    for prop, stats in SHARED_ROLLS.items():
        specs = [s for s in definition.get('roll_ranges', {}).values() if s.get('property') == prop]
        if {s['stat_id'] for s in specs} != stats:
            continue
        rows = [facts.stats.get(f'{s["stat_id"]}:{s.get("layer", 0)}', {}) for s in specs]
        values = [r.get('value') for r in rows]
        if (
            any(r.get('status') != 'decoded' for r in rows)
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
            or any(v != values[0] for v in values)
        ):
            gaps.append(f'Named {prop} components do not establish one shared roll.')
    return gaps
