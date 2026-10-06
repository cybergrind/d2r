"""Equip level of ordinary jewels from validated captured affix identities."""

from inventory_tracking.items.metadata import metadata


def required_level(facts):
    # Ordinary Jewel has levelreq=0 in native misc. Colossal/unique jewels,
    # crafts and socketable equipment have other requirement contributions.
    if facts.base_name != 'Jewel' or not facts.capture_complete or not facts.native_affixes:
        return None
    if facts.native_affixes['auto'] or facts.sockets not in (None, 0):
        return None
    if facts.socket_contents == 'filled' or any(k in facts.stats for k in ('92:0', '94:0')):
        return None
    entries = [metadata()['affixes'][table][str(i)] for table, ids in facts.native_affixes.items() for i in ids]
    if facts.rarity == 'rare' and len(entries) > 4:
        return None
    levels = [entry['game_definition'].get('levelreq') for entry in entries]
    groups = [entry['game_definition'].get('group') for entry in entries]
    if any(type(level) is not int or not 0 <= level <= 99 for level in levels):
        return None
    if None in groups or len(set(groups)) != len(groups):
        return None
    return max(levels)
