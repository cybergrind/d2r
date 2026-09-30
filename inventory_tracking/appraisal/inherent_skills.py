"""Amazon base skill-tab ranges without borrowing magic affixes or all-skills."""

from inventory_tracking.appraisal.runeword_rolls import verified_recipe
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.definition_store import catalog


def display_inherent_skills(extraction, rows):
    if not extraction.get('item') or not any(
        row.get('memory_stat', {}).get('id') == 188 and 'roll_range' not in row for row in rows
    ):
        return rows
    facts = normalize(extraction)
    if facts.identified is not True or facts.rarity not in ('normal', 'superior', 'low_quality'):
        return rows
    definition = None
    family, _ = classify(facts)
    if facts.runeword:
        definition = catalog().runewords.get(facts.runeword)
        if not definition or not verified_recipe(facts, definition, family):
            return rows
    elif facts.socket_contents != 'empty':
        return rows
    entries = [e for e in metadata()['affixes']['auto'].values() if facts.base_code in e['base_codes']]
    displayed = []
    for original in rows:
        native = original.get('memory_stat', {})
        key = f'188:{native.get("layer")}'
        if native.get('id') != 188 or 'roll_range' in original:
            displayed.append(original)
            continue
        candidates = [(e, e['roll_ranges'][key]) for e in entries if key in e['roll_ranges']]
        if not candidates or any(d.get('property') != 'skilltab' for _, d in candidates):
            displayed.append(original)
            continue
        low = min(d['min'] for _, d in candidates)
        high = max(d['max'] for _, d in candidates)
        if definition:
            # A recipe can grant the same tab (e.g. Melody). Keep its verified
            # contribution distinct from unrelated +all-skills or class skills.
            recipe = definition.get('roll_ranges', {}).get(key, {})
            rune = definition.get('socket_bonus_ranges', {}).get(family, {}).get(key, {})
            low += recipe.get('min', 0) + rune.get('min', 0)
            high += recipe.get('max', 0) + rune.get('max', 0)
        row = dict(original)
        annotate_roll_ranges(
            [row],
            {
                'roll_ranges': {key: {'stat_id': 188, 'layer': native['layer'], 'min': low, 'max': high}},
                'source': [e['source'] for e, _ in candidates],
                'scope': 'native base skill tab' + (' plus verified runeword contribution' if definition else ''),
            },
        )
        displayed.append(row)
    return displayed
