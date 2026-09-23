"""Decode captured item bases and stat entries using offline metadata.

Memory stat IDs and market property IDs are separate namespaces. Unverified
identity fields and parameter encodings stay explicit; no memory access here.
"""

from typing import Any

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.containers import container_for_page
from inventory_tracking.items.context import viewer_context
from inventory_tracking.items.defense import defense_range_context
from inventory_tracking.items.identity import (
    ETHEREAL_FLAG,
    IDENTIFIED_FLAG,
    RUNEWORD_FLAG,
    SOCKETED_FLAG,
    identity_review,
    item_flags,
    resolve_identity,
)
from inventory_tracking.items.metadata import decode_stats, item_base, metadata
from inventory_tracking.items.owners import require_mercenary_owner
from inventory_tracking.items.ranges import annotate_roll_ranges
from inventory_tracking.items.sockets import annotate_sockets
from inventory_tracking.items.staffmods import annotate_staffmods
from inventory_tracking.native.layout import SUPPORTED_SHA256
from inventory_tracking.tracking.state import select_player


# Observed on build 1e2ac459..., unit 438836750, array +0xE8; screenshot comparison.
# Property IDs/labels verified from local appraisal-properties.json.
RING_CLASS = 537  # Local d2data misc.json classid, code rin.


def decode_items(
    snapshot, report, *, inventory_page=0, rings_only=False, inventory_owner_id=None, inventory_owner_type=0
):
    """Return owned inventory item observations; unknown fields stay unknown."""
    container = container_for_page(inventory_page, owner_type=inventory_owner_type)
    if report.get('game', {}).get('executable_fingerprint', {}).get('sha256') != SUPPORTED_SHA256:
        raise ValueError('Unsupported game build')
    if report.get('state') != 'complete' or snapshot.get('status') != 'research':
        raise ValueError('Incomplete or stale capture')
    if not snapshot.get('identity') or snapshot['identity'] != report.get('game', {}).get('identity'):
        raise ValueError('Capture process identity mismatch')
    groups = snapshot.get('groups', {})
    resources = snapshot.get('resources', {})
    if (
        not snapshot.get('mappings_stable')
        or not resources.get('complete')
        or not all(groups.get(name, {}).get('complete') for name in ('players', 'items'))
    ):
        raise ValueError('Unstable item snapshot')
    player_id, _ = select_player(groups['players']['units'])
    owner_id = player_id if inventory_owner_id is None else inventory_owner_id
    mercenary = inventory_owner_type == 1 and inventory_page == 255
    shop = inventory_owner_type == 1 and not mercenary
    if mercenary:
        require_mercenary_owner(snapshot, owner_id, player_id)
    elif shop:
        monsters = groups.get('monsters', {})
        owners = [
            u
            for u in monsters.get('units', [])
            if u['unit_id'] == owner_id and u['type'] == 1 and u.get('identity_stable')
        ]
        if inventory_owner_id is None or not monsters.get('complete') or len(owners) != 1:
            raise ValueError('Unverified shop owner')
    elif owner_id != player_id:
        owners = [u for u in groups['players']['units'] if u['unit_id'] == owner_id and u.get('identity_stable')]
        if inventory_page != 4 or len(owners) != 1 or owners[0]['type'] != 0:
            raise ValueError('Unsupported inventory owner')
    if inventory_page == 4:
        container['name'] = 'Personal stash' if owner_id == player_id else 'Shared stash'
    viewer = viewer_context(snapshot)
    results: list[dict[str, Any]] = []
    for row in resources.get('items', []):
        details = row['details']
        if (
            (rings_only and (row['txt_id'] != RING_CLASS or details.get('quality') != 4))
            or row['mode'] != (1 if inventory_page == 255 else 0)
            or details.get('owner_id') != (0xFFFFFFFF if shop or mercenary else owner_id)
            or details.get('inventory_page') != inventory_page
        ):
            continue
        arrays = row.get('resource_stats', {})
        candidates = [a for a in arrays.get('arrays', []) if a.get('header_offset') == 0xE8]
        if not arrays.get('complete') or len(candidates) != 1 or not isinstance(candidates[0].get('stats'), list):
            raise ValueError('Item stat array missing or changed')
        stats = list(candidates[0]['stats'])
        extra_damage = arrays.get('damage_modifiers', [])
        used_local_damage = bool(extra_damage) and not any(s['id'] in (17, 18) for s in stats)
        if used_local_damage:
            stats.extend(extra_damage)
        base = item_base(row['txt_id'])
        if base is None:
            raise ValueError(f'Unknown item class {row["txt_id"]}; metadata update required')
        extra_defense = arrays.get('defense_modifiers', [])
        used_local_defense = bool(extra_defense) and not any(s['id'] == 16 for s in stats)
        if used_local_defense:
            stats.extend(extra_defense)
        decoded, affixes, unresolved = decode_stats(stats, base=base, viewer_level=(viewer or {}).get('level'))
        if used_local_defense:
            for component in [*decoded, *affixes]:
                if component.get('memory_stat') in extra_defense:
                    component.pop('descriptor_offset', None)
                    component['origin'] = 'owned_modifier_list'
                    component['modifier_head_offset'] = 0xD0
        if used_local_damage:
            for component in [*decoded, *affixes]:
                if component.get('memory_stats') == extra_damage:
                    component.pop('descriptor_offset', None)
                    component['origin'] = 'owned_modifier_list'
                    component['modifier_head_offset'] = 0xD0
        rarity = {
            1: 'low quality',
            2: 'normal',
            3: 'superior',
            4: 'magic',
            5: 'set',
            6: 'rare',
            7: 'unique',
            8: 'crafted',
            9: 'tempered',
        }.get(details.get('quality'))
        if rarity is None:
            raise ValueError('Unknown item quality')
        identity = resolve_identity(details, arrays, base)
        flags = item_flags(details, arrays)
        range_context: dict[str, Any] | None = (
            identity if identity and identity['table'] != 'rare' else resolve_affix_ranges(details, arrays, base)
        )
        annotate_roll_ranges(decoded, range_context)
        annotate_roll_ranges(decoded, defense_range_context(arrays, identity))
        annotate_staffmods(decoded, details, arrays, base)
        results.append(
            {
                'item': {
                    'name': identity['name'] if identity else base['name'],
                    **({'set_name': identity['set_name']} if identity and identity.get('set_name') else {}),
                    **({'runeword': identity['name']} if identity and identity['table'] == 'runeword' else {}),
                    'base_name': base['name'],
                    'base_code': base['code'],
                    'category': base['category'],
                    'rarity': rarity,
                    'requirements': {},
                    'affixes': affixes,
                    'sockets': None,
                    'ethereal': bool(flags & ETHEREAL_FLAG) if flags is not None else None,
                    'socket_contents': None,
                },
                'source': {
                    'engine': 'memory_snapshot',
                    **({'viewer_context': viewer} if viewer else {}),
                    **(
                        {'item_identity': {k: identity[k] for k in ('table', 'table_id', 'offset')}} if identity else {}
                    ),
                    'container': container,
                    'unit_id': row['unit_id'],
                    'owner_id': owner_id,
                    'owner_type': inventory_owner_type,
                    'item_owner_id': details.get('owner_id'),
                    'player_id': player_id,
                    'position': [details.get('x'), details.get('y')],
                    'run_id': report.get('run_id'),
                    'captured_at': report.get('finished_at'),
                    'snapshot_only': True,
                    'build_sha256': SUPPORTED_SHA256,
                },
                'unresolved_stats': unresolved,
                'decoded_stats': decoded,
                'review': [
                    *(range_context or {}).get('review', []),
                    *(
                        ['Title, required level, flags and general affix coverage are not decoded.']
                        if rings_only
                        else identity_review(identity, stats)
                    ),
                    'Tooltip attack-speed category is not reconstructed; base-type bonuses are labeled separately.',
                    'Values are from the captured total stat array; socket/set contributions are not separated.',
                    'Snapshot evidence is historical; it does not establish current inventory state.',
                ],
                'appraisal_ready': False,
                'offline': True,
                'status': 'needs_review',
            }
        )
        annotate_sockets(results[-1]['item'], decoded, arrays, identity)
        children = arrays.get('socket_items', {})
        if (
            flags is not None
            and not flags & SOCKETED_FLAG
            and not any(s['id'] == 194 for s in stats)
            and children.get('complete') is True
            and children.get('children') == []
        ):
            results[-1]['item'].update(sockets=0, empty_sockets=0, filled_sockets=0, socket_contents='empty')
        item = results[-1]['item']
        if (
            details.get('quality') == 3
            and flags is not None
            and identity is None
            and flags & IDENTIFIED_FLAG
            and not flags & RUNEWORD_FLAG
            and item.get('socket_contents') == 'empty'
        ):
            annotate_roll_ranges(decoded, metadata()['superior'].get(base['category']))
    if not results:
        raise ValueError(
            'No owned inventory magic rings in this capture'
            if rings_only
            else 'No owned inventory items in this capture'
        )
    return results


def decode_rings(snapshot, report, *, inventory_page=0):
    """Compatibility entry point for historical ring captures."""
    return decode_items(snapshot, report, inventory_page=inventory_page, rings_only=True)
