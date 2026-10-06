"""Displayed enhancement totals for same-base completed-runeword comparisons."""

from pricing.knowledge.assessment.registry import FAMILIES


def total_definition(definition, base_code, game):
    base = next((b for b in game.get('bases', {}).values() if b['code'] == base_code), None)
    if base is None:
        return definition
    family = next((f.name for f in FAMILIES if base['type'] in f.types), None)
    runes = definition.get('socket_bonus_ranges', {}).get(family, {})
    quality = game.get('superior', {}).get(base['category'], {}).get('roll_ranges', {})
    ranges = dict(definition.get('roll_ranges', {}))
    for key, spec in ranges.items():
        stat = str(spec.get('stat_id', key.split(':')[0]))
        enhancement = (stat in ('17', '18') and family == 'weapon') or (
            stat == '16' and family in ('armor', 'helm', 'shield')
        )
        if not enhancement or spec['min'] == spec['max']:
            continue
        rune = runes.get(key, {})
        # Compare totals directly. Do not subtract an assumed superior roll
        # or claim that a total identifies the runeword's individual roll.
        ranges[key] = spec | {
            'min': spec['min'] + rune.get('min', 0),
            'max': spec['max'] + rune.get('max', 0) + quality.get(stat, {}).get('max', 0),
        }
    return definition | {'roll_ranges': ranges}
