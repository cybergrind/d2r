"""Viewer context for tooltip formulas; never use a shared-stash owner's level."""

from inventory_tracking.tracking.state import select_player


def viewer_context(snapshot):
    players = snapshot.get('groups', {}).get('players', {})
    if not players.get('complete') or not snapshot.get('mappings_stable'):
        return None
    player_id, _ = select_player(players['units'])
    candidates = [p for p in players['units'] if p['unit_id'] == player_id and p.get('identity_stable')]
    if len(candidates) != 1:
        return None
    levels = [s['raw'] for s in candidates[0]['details'].get('full_stats', []) if s['id'] == 12 and s['layer'] == 0]
    if len(levels) != 1 or type(levels[0]) is not int or not 1 <= levels[0] <= 99:
        return None
    return {'player_id': player_id, 'level': levels[0]}
