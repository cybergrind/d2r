"""Validate research snapshots into domain state."""

from typing import Any

from .belt import potion_kind
from .config import RESOURCE_READER, ResourceReaderConfig
from .layout import BELT_COLUMNS, BELT_ITEM_MODE, BELT_SIZE, LIFE_STAT, MAX_LIFE_STAT
from .mercenary import select_mercenary
from .models import BeltCell, BeltSnapshot, PlayerHealth, PotionType, SessionIdentity, State
from .resources import resource_observations


type Snapshot = dict[str, Any]


class IncompleteRead(ValueError):
    """The snapshot cannot yield a complete sample; the message is the published reason."""


def life_stats(stats: object) -> tuple[int, int] | None:
    """(current, maximum) from a unit's layer-0 stats, or None when absent, duplicated or implausible."""
    if not isinstance(stats, list):
        return None
    life = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == LIFE_STAT]
    maximum = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == MAX_LIFE_STAT]
    if len(life) == len(maximum) == 1 and 0 <= life[0] <= maximum[0] and maximum[0] > 0:
        return life[0], maximum[0]
    return None


def select_player(players: list[Snapshot]) -> tuple[int, PlayerHealth]:
    """Exactly one player unit with plausible life is the local player (single-player only)."""
    candidates = [
        (player['unit_id'], PlayerHealth(*health))
        for player in players
        if (health := life_stats(player['details'].get('full_stats'))) is not None
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not players:
        raise IncompleteRead('outside game')
    raise IncompleteRead('ambiguous player' if candidates else 'health unavailable')


def read_identity(snapshot: Snapshot, player_id: int) -> SessionIdentity:
    identity = snapshot.get('identity', {})
    if not identity.get('pid') or not identity.get('start_ticks'):
        raise IncompleteRead('identity unavailable')
    return SessionIdentity(identity['pid'], identity['start_ticks'], player_id)


def read_belt(items: list[Snapshot], player_id: int) -> BeltSnapshot:
    """The player's belt by cell, plus the bottom-row potions reachable by hotkey column."""
    contents: list[int | None] = [None] * BELT_SIZE
    cells: set[int] = set()
    item_ids: set[int] = set()
    healing_cells = []
    rejuvenation_cells = []
    for item in items:
        details = item['details']
        if item['mode'] != BELT_ITEM_MODE or details.get('owner_id') != player_id:
            continue
        cell = details.get('x')
        if (
            type(cell) is not int
            or not 0 <= cell < BELT_SIZE
            or details.get('y') != 0
            or cell in cells
            or item['unit_id'] in item_ids
        ):
            raise IncompleteRead('inconsistent belt')
        contents[cell] = item['txt_id']
        cells.add(cell)
        item_ids.add(item['unit_id'])
        kind = potion_kind(item['txt_id'])
        if cell < BELT_COLUMNS:
            if kind == PotionType.HEALING:
                healing_cells.append(BeltCell(cell + 1, item['unit_id']))
            elif kind == PotionType.REJUVENATION:
                rejuvenation_cells.append(BeltCell(cell + 1, item['unit_id']))
    return BeltSnapshot(
        contents=tuple(contents),
        healing_cells=tuple(sorted(healing_cells)),
        rejuvenation_cells=tuple(sorted(rejuvenation_cells)),
        item_ids=tuple(sorted(item_ids)),
    )


def from_research(snapshot: Snapshot, *, resource_config: ResourceReaderConfig = RESOURCE_READER) -> State:
    sampled = snapshot['sample_monotonic']
    groups = snapshot['groups']
    try:
        if snapshot['status'] != 'research' or not all(g['complete'] for g in groups.values()):
            raise IncompleteRead('incomplete read')
        player_id, health = select_player(groups['players']['units'])
        session = read_identity(snapshot, player_id)
        belt = read_belt(groups['items']['units'], player_id)
    except IncompleteRead as exc:
        return State(sampled_at=sampled, reason=str(exc))
    resources = resource_observations(snapshot, player_id, config=resource_config)
    # User authorized healing without in-game menu detection (2026-09-21).
    # The research UI flag is invalid for this build and must not gate input.
    return State(
        sampled_at=sampled,
        session=session,
        health=health,
        merc=select_mercenary(groups.get('monsters', {}).get('units', []), player_id),
        belt=belt,
        teleport=resources.teleport,
        portal_tome=resources.portal_tome,
        identify_tome=resources.identify_tome,
        location=resources.location,
        keys=resources.keys,
    )
