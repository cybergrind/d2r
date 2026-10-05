"""Charm poison tiers retain both native rate and duration, including paired affixes."""

from itertools import product

from inventory_tracking.items.poison import DAMAGE_SCALE, FRAMES_PER_SECOND


def poison_modifier(entry):
    game = entry.get('game_definition', {})
    slots = [i for i in range(1, 4) if game.get(f'mod{i}code') == 'dmg-pois']
    if len(slots) != 1:
        return None
    i = slots[0]
    rate, maximum, frames = (game.get(f'mod{i}{key}') for key in ('min', 'max', 'param'))
    # Charm poison tiers are fixed rates, not independently rolled endpoints.
    if any(type(v) is not int or v <= 0 for v in (rate, maximum, frames)) or rate != maximum:
        return None
    return rate, frames


def poison_range(entries, base, quality, catalog):
    if quality != 4 or base.get('type') not in ('scha', 'mcha', 'lcha'):
        return None
    contributors = [(entry, poison_modifier(entry)) for entry in entries if poison_modifier(entry)]
    if not contributors or len({e['affix_table'] for e, _ in contributors}) != len(contributors):
        return None
    pools = []
    for entry, _ in contributors:
        pool = {
            mod
            for candidate in catalog['affixes'][entry['affix_table']].values()
            if candidate.get('spawnable')
            and base['code'] in candidate['base_codes']
            and candidate['game_definition'].get('group') == entry['game_definition'].get('group')
            and (mod := poison_modifier(candidate))
        }
        if not pool:
            return None
        pools.append(pool)
    selected = tuple(sum(mod[i] for _, mod in contributors) for i in (0, 1))
    tiers = {tuple(sum(part[i] for part in parts) for i in (0, 1)) for parts in product(*pools)}
    if selected not in tiers:
        return None
    return {
        'selected': selected,
        'tiers': sorted(tiers, key=lambda t: (damage(*t), t[0], t[1]), reverse=True),
        'affix_kind': contributors[0][0]['affix_table'].title() if len(contributors) == 1 else 'Combined',
        'source': [entry['source'] for entry, _ in contributors],
    }


def damage(rate, frames):
    return (rate * frames + DAMAGE_SCALE // 2) // DAMAGE_SCALE


def annotate_poison_range(decoded, definition):
    if not definition:
        return
    rate, frames = definition['selected']
    if frames % FRAMES_PER_SECOND:
        return
    tiers = definition['tiers']
    high, low = damage(*tiers[0]), damage(*tiers[-1])
    value = damage(rate, frames)
    for row in decoded:
        if row.get('name') != 'poison_damage' or row.get('status') != 'decoded':
            continue
        native = row.get('memory_stats', [])
        if len(native) != 4 or any(s['layer'] != 0 for s in native):
            continue
        if {s['id']: s['raw'] for s in native} != {57: rate, 58: rate, 59: frames, 326: 1}:
            continue
        tier = tiers.index((rate, frames)) + 1
        row['roll_range'] = {
            'min': value,
            'max': value,
            'quality_range': {'min': low, 'max': high},
            'tiers': [{'min': damage(*t), 'max': damage(*t), 'seconds': t[1] / FRAMES_PER_SECOND} for t in tiers],
            'source': definition['source'],
            'scope': 'captured poison affix combination; all tiers for this charm size',
        }
        row['roll_tier'] = tier
        row['roll_tier_count'] = len(tiers)
        row['roll_quality'] = (
            'perfect' if value == high else 'low' if high > low and (value - low) / (high - low) <= 0.2 else 'normal'
        )
        best_seconds = tiers[0][1] / FRAMES_PER_SECOND
        row['text'] = (
            f'+{value} ({low}-{high}) Poison Damage over {frames // FRAMES_PER_SECOND} Seconds '
            f'[{definition["affix_kind"]} T{tier}; T1: {high} over {best_seconds:g} Seconds]'
        )
