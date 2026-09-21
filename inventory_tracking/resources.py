"""Decode optional item/location facts using supported-build resource settings."""

from collections.abc import Callable
from typing import Any, NamedTuple

from .config import RESOURCE_READER, ResourceReaderConfig
from .layout import (
    CHARGED_SKILL_STAT,
    QUANTITY_STAT,
    STAFF_CLASS_IDS,
    TELEPORT_SKILL,
    TOME_CLASS_ID,
    TOWN_IDS,
    WEAPON_SLOTS,
)
from .models import Location, Observation, PortalTome, TeleportCharges


def item_stats(item, offset):
    research = item.get('resource_stats', {})
    if not research.get('complete'):
        raise ValueError('Item stats unavailable or changed')
    arrays = [array['stats'] for array in research['arrays'] if array['header_offset'] == offset]
    if len(arrays) != 1:
        raise ValueError('Expected one verified item stat descriptor')
    return arrays[0]


def select_portal(items, config):
    if config.portal_stats_offset is None:
        raise ValueError('Portal quantity layout not verified')
    matches = [
        item
        for item in items
        if item['txt_id'] == TOME_CLASS_ID and item['mode'] == 0 and item['details'].get('inventory_page') == 0
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError('Ambiguous portal tome')
    item = matches[0]
    values = [
        stat['raw']
        for stat in item_stats(item, config.portal_stats_offset)
        if stat['id'] == QUANTITY_STAT and stat['layer'] == 0
    ]
    if len(values) != 1:
        raise ValueError('Portal quantity unavailable')
    return PortalTome(item['unit_id'], values[0], 20)


def select_teleport(items, config):
    if config.teleport_stats_offset is None or not config.weapon_slots_verified:
        raise ValueError('Secondary staff charge layout not verified')
    matches = []
    for item in items:
        if (
            item['txt_id'] not in STAFF_CLASS_IDS
            or item['mode'] != 1
            or item['details'].get('body_location') not in WEAPON_SLOTS
        ):
            continue
        for stat in item_stats(item, config.teleport_stats_offset):
            if stat['id'] == CHARGED_SKILL_STAT and stat['layer'] >> 6 == TELEPORT_SKILL:
                raw = stat['raw']
                if type(raw) is not int or not 0 <= raw <= 0xFFFF:
                    raise ValueError('Invalid packed charge value')
                matches.append(TeleportCharges(item['unit_id'], raw & 0xFF, raw >> 8))
    if len(matches) > 1:
        raise ValueError('Ambiguous Teleport charge source')
    return matches[0] if matches else None


def select_location(records, player_id, config):
    if not config.location_verified:
        raise ValueError('Town location layout not verified')
    matches = [entry for entry in records if entry['unit_id'] == player_id]
    if len(matches) != 1 or 'area_id' not in matches[0]:
        raise ValueError('Player location unavailable')
    area = matches[0]['area_id']
    if type(area) is not int or not 1 <= area <= 1024:
        raise ValueError('Invalid area ID')
    return Location(area, area in TOWN_IDS)


class ResourceObservations(NamedTuple):
    teleport: Observation[TeleportCharges]
    portal_tome: Observation[PortalTome]
    location: Observation[Location]


def resource_observations(
    snapshot: dict[str, Any], player_id: int, *, config: ResourceReaderConfig = RESOURCE_READER
) -> ResourceObservations:
    sampled = snapshot['sample_monotonic']
    research: dict[str, Any] = snapshot.get('resources', {})
    if not isinstance(research, dict):
        research = {'reason': 'Malformed resource records'}
    if snapshot['status'] != 'research' or not research.get('complete'):
        reason = research.get('reason', 'resources not sampled')
        return ResourceObservations(
            Observation.unavailable(sampled, reason),
            Observation.unavailable(sampled, reason),
            Observation.unavailable(sampled, reason),
        )

    def owned_items() -> list[dict[str, Any]]:
        return [item for item in research['items'] if item['details']['owner_id'] == player_id]

    def observe[T](select: Callable[[], T | None]) -> Observation[T]:
        try:
            return Observation(sampled, select())
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return Observation.unavailable(sampled, str(exc))

    return ResourceObservations(
        teleport=observe(lambda: select_teleport(owned_items(), config)),
        portal_tome=observe(lambda: select_portal(owned_items(), config)),
        location=observe(lambda: select_location(research.get('locations', []), player_id, config)),
    )
