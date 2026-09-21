"""Validate research snapshots into domain state."""

from .belt import potion_kind
from .mercenary import select_mercenary
from .models import BeltCell, PotionType, State


def from_research(snapshot):
    sampled = snapshot['sample_monotonic']
    groups = snapshot['groups']
    if snapshot['status'] != 'research' or not all(g['complete'] for g in groups.values()):
        return State(sampled, reason='incomplete read')
    candidates = []
    for player in groups['players']['units']:
        stats = player['details'].get('full_stats')
        if not isinstance(stats, list):
            continue
        life = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == 6]
        maximum = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == 7]
        if len(life) == len(maximum) == 1 and 0 <= life[0] <= maximum[0] and maximum[0] > 0:
            candidates.append((player['unit_id'], life[0], maximum[0]))
    if len(candidates) != 1:
        reason = 'ambiguous player' if candidates else 'health unavailable'
        if not groups['players']['units']:
            reason = 'outside game'
        return State(sampled, reason=reason)
    player_id, current, maximum = candidates[0]
    belt_contents = [None] * 16
    cells = set()
    item_ids = set()
    healing_cells = []
    rejuvenation_cells = []
    for item in groups['items']['units']:
        details = item['details']
        if item['mode'] != 2 or details.get('owner_id') != player_id:
            continue
        cell = details.get('x')
        if (
            type(cell) is not int
            or not 0 <= cell < 16
            or details.get('y') != 0
            or cell in cells
            or item['unit_id'] in item_ids
        ):
            return State(sampled, reason='inconsistent belt')
        belt_contents[cell] = item['txt_id']
        cells.add(cell)
        item_ids.add(item['unit_id'])
        kind = potion_kind(item['txt_id'])
        if cell < 4:
            if kind == PotionType.HEALING:
                healing_cells.append(BeltCell(cell + 1, item['unit_id']))
            elif kind == PotionType.REJUVENATION:
                rejuvenation_cells.append(BeltCell(cell + 1, item['unit_id']))
    merc = select_mercenary(groups.get('monsters', {}).get('units', []), player_id)
    identity = snapshot.get('identity', {})
    return State(
        sampled,
        current,
        maximum,
        player_id=player_id,
        merc=merc,
        process_id=identity.get('pid'),
        process_start=identity.get('start_ticks'),
        belt_contents=tuple(belt_contents),
        healing_cells=tuple(sorted(healing_cells)),
        rejuvenation_cells=tuple(sorted(rejuvenation_cells)),
        # User authorized healing without in-game menu detection (2026-09-21).
        # The research UI flag is invalid for this build and must not gate input.
        gameplay_ready=bool(identity.get('pid') and identity.get('start_ticks') and current > 0),
        belt_ids=tuple(sorted(item_ids)),
    )
