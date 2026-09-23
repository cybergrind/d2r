"""Validate mercenary equipment owners independently of vendor inventories."""

from inventory_tracking.native.layout import HIRELING_CLASS_ID


def require_mercenary_owner(snapshot, owner_id, player_id):
    # This monster-data association is host-verified for Act 2 hirelings. Other
    # hireling layouts must be captured before extending the supported classes.
    monsters = snapshot.get('groups', {}).get('monsters', {})
    matches = [u for u in monsters.get('units', []) if u.get('type') == 1 and u.get('unit_id') == owner_id]
    if not monsters.get('complete') or len(matches) != 1:
        raise ValueError('Incomplete or ambiguous mercenary owner')
    owner = matches[0]
    data = owner.get('details', {}).get('monster_data_u32', [])
    if (
        not owner.get('identity_stable')
        or owner.get('txt_id') != HIRELING_CLASS_ID
        or len(data) <= 21
        or data[21] != player_id
    ):
        raise ValueError('Equipment is not owned by the local mercenary')
    return owner
