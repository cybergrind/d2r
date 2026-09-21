"""Toolkit-independent OSD values; the research selector is not controller-ready."""

from dataclasses import dataclass

from ..mercenary import Mercenary, select_mercenary


MERC_HEALTH_DISPLAY_BELOW_PERCENT = 65


@dataclass(frozen=True)
class State:
    sampled_at: float
    current_raw: int | None = None
    maximum_raw: int | None = None
    rejuvenations: int = 0
    healing: int = 0
    reason: str = ''
    player_id: int | None = None
    merc: Mercenary | None = None
    process_id: int | None = None
    process_start: str | None = None
    belt_contents: tuple[int | None, ...] | None = None
    healing_cells: tuple = ()
    rejuvenation_cells: tuple = ()
    # Complete living-player sample with process identity; not a menu check.
    gameplay_ready: bool = False
    belt_ids: tuple = ()
    player_potion_sent: tuple[float, int] | None = None
    merc_potion_sent: tuple[float, int] | None = None


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
    rejuvenations = healing = 0
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
        # Verified d2data class IDs; see ../layout_notes.md. Count belt stock only.
        rejuvenations += item['txt_id'] == 531
        healing += item['txt_id'] == 606
        # Standard healing tiers 602-606 verified in cached d2data misc.json.
        if item['txt_id'] in (602, 603, 604, 605, 606) and cell < 4:
            healing_cells.append((cell + 1, item['unit_id']))
        # Rejuvenation class IDs 530/531 verified in cached d2data misc.json.
        if item['txt_id'] in (530, 531) and cell < 4:
            rejuvenation_cells.append((cell + 1, item['unit_id']))
    merc = select_mercenary(groups.get('monsters', {}).get('units', []), player_id)
    identity = snapshot.get('identity', {})
    return State(
        sampled,
        current,
        maximum,
        rejuvenations,
        healing,
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


def potion_kind(class_id):
    if class_id in (530, 531):
        return 'juv'
    if class_id in (602, 603, 604, 605, 606):
        return 'hp'
    return None


def column_shortages(contents):
    """Bottom potion defines each four-slot column; entirely empty means juv."""
    missing = {'juv': 0, 'hp': 0}
    for column in range(4):
        slots = contents[column::4]
        # If the bottom has a gap, use the lowest remaining item as the target.
        first = next((item for item in slots if item is not None), None)
        kind = 'juv' if first is None else potion_kind(first)
        if kind is not None:
            missing[kind] += sum(potion_kind(item) != kind for item in slots)
    return missing['juv'], missing['hp']


def display_lines(state, *, now, max_age=2.0, rejuvenation_target=None, healing_target=None):
    lines = []
    if state.player_potion_sent is not None:
        sent_at, column = state.player_potion_sent
        if 0 <= now - sent_at < 1:
            lines.append(f'player potion sent ({column})')
    if state.merc_potion_sent is not None:
        sent_at, column = state.merc_potion_sent
        if 0 <= now - sent_at < 1:
            lines.append(f'merc potion sent (Shift+{column})')
    if state.current_raw is None or not 0 <= now - state.sampled_at <= max_age:
        return lines
    if state.current_raw * 100 <= state.maximum_raw * 70:
        lines.append(f'{state.current_raw >> 8}/{state.maximum_raw >> 8}')
    if state.merc is not None:
        if not state.merc.alive:
            lines.append('merc dead')
        elif state.merc.life_fraction_raw * 100 < 32768 * MERC_HEALTH_DISPLAY_BELOW_PERCENT:
            prefix = '' if state.merc.life_fraction_raw == 32768 else '~'
            lines.append(f'merc {prefix}{state.merc.current_raw >> 8}/{state.merc.maximum_raw >> 8}')
    if state.belt_contents is not None:
        missing_rejuvenations, missing_healing = column_shortages(state.belt_contents)
    else:
        missing_rejuvenations = max(0, 8 - state.rejuvenations)
        missing_healing = max(0, 8 - state.healing)
    if rejuvenation_target is not None:
        missing_rejuvenations = max(0, rejuvenation_target - state.rejuvenations)
    if healing_target is not None:
        missing_healing = max(0, healing_target - state.healing)
    if missing_rejuvenations:
        lines.append(f'juv {missing_rejuvenations}')
    if missing_healing:
        lines.append(f'hp {missing_healing}')
    return lines
