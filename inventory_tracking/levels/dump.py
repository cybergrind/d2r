"""Win+C handling inside the Alt+D worker process: dump the current level's structures.

The compositor binding sends `level <monotonic>` to the appraisal socket. The memory
pass runs under the shared capture lock, then `level.json` (research, unvalidated)
and `report.json` land in a new run directory under `runs/level/`; `latest.json`
points at the newest one so an agent can pick it up without a chat reply.

Besides the research survey, the dump carries an `evidence` section: the confirmed
reader's snapshot plus what the area's handler finds (levels/evidence.py), which converts
straight into a test fixture. The notification leads with that result.
"""

import math
import threading
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG, timestamp
from inventory_tracking.levels.evidence import evidence_record
from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.memory import observe_level
from inventory_tracking.levels.model import LevelSnapshot
from inventory_tracking.levels.presets import level_name
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.research import dump_level
from inventory_tracking.reports import create_run, publish


DEFAULT_OUTPUT = Path('inventory_tracking/runs/level')
REQUEST_PREFIX = 'level '


def describe(summary: dict[str, Any]) -> tuple[str, str]:
    title = (
        f'Level {summary["level_no"]}: {summary["room2s_in_level"]} Room2s, {summary["loaded_room1s_in_level"]} loaded'
    )
    body = (
        f'{summary["levels_with_room2s"]}/{summary["levels_in_act_chain"]} act levels hold Room2s; '
        f'units {summary["units"]}; typed marker hits {summary["typed_marker_hits"]}; '
        f'Summoner unit {"seen" if summary["summoner_unit_seen"] else "not seen"}'
    )
    if 'collision_rooms' in summary:  # walkability research: loaded rooms with a collision-mask candidate
        body += f'; collision candidates in {summary["collision_rooms"]}/{summary["loaded_room1s_in_level"]} rooms'
    shrines = summary.get('shrine_candidates') or []
    if shrines:  # candidate decode (research.shrine_candidate), for checking against the game
        body += '; shrines: ' + ', '.join(shrine['name'] for shrine in shrines)
    runes = [item['rune'] for item in summary.get('ground_items') or [] if item.get('rune')]
    if runes:  # ground mode/position are unconfirmed (loot/ground.py): compare with the drop in game
        body += '; ground runes: ' + ', '.join(runes)
    return title, body


def level_evidence(pid, images, capture, observe=observe_level) -> tuple[dict[str, Any], str]:
    """The confirmed reader's view plus the handler result, and a one-line headline for it."""
    try:
        location, rooms = observe(pid, images, capture, rooms=True)
    except Exception as exc:
        return {'error': str(exc)}, 'Level guidance unavailable'
    if location is None:
        return {'error': 'no player location'}, 'Level guidance unavailable'
    snapshot = LevelSnapshot(location, tuple(rooms))
    name = level_name(location.area_id)
    handler = handler_for(location.area_id)
    touched = list(dict.fromkeys(area for room in snapshot.rooms for area in room.leads_to))
    touches = f'; touches {", ".join(level_name(area) for area in touched)}' if touched else ''
    if handler is None:
        record = {
            'area_id': location.area_id,
            'level_name': name,
            'handler': None,
            'player': {'x': location.x, 'y': location.y},
            'rooms': [r.row() for r in snapshot.rooms],
        }
        return record, f'{name}: no handler{touches}'
    guidance = guide_level(handler, snapshot)
    found = [pointer(poi, location) for poi in guidance.pois]
    parts = [f'• {p.label} here' if p.here else f'{p.arrow} {p.label} {p.compass}' for p in found]
    parts += list(guidance.problems)
    status = '' if handler.confirmed else ' (unconfirmed)'
    headline = f'{name}{status}: {"; ".join(parts) or "nothing found"}{touches}'
    return evidence_record(snapshot, handler, guidance), headline


class LevelDumper:
    """One dump at a time, fresh requests only; failures are reported, never retried."""

    def __init__(
        self, source, output: Path, *, capture_lock: threading.Lock, notify, dump=dump_level, observe=observe_level
    ):
        self.source, self.output = source, output
        self.capture_lock, self.notify, self.dump, self.observe = capture_lock, notify, dump, observe
        self.last_request = -math.inf

    def request(self, requested_at: float, now: float, *, announce: bool = True) -> bool:
        """`announce=False` skips the desktop notification (the OSD card already shows the result)."""
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1 or now - self.last_request < 1:
            return False
        self.last_request = now
        directory, report = create_run(self.output)
        try:
            with self.capture_lock:
                self.source.ensure_connected()
                result = self.dump(self.source.pid, self.source.images, self.source.capture)
                result['evidence'], title = level_evidence(
                    self.source.pid, self.source.images, self.source.capture, self.observe
                )
            publish(directory / 'level.json', result)
            report.update(state='complete', summary=result['summary'], guidance=title)
            research_title, research_body = describe(result['summary'])
            body = f'{research_title}. {research_body}'
        except Exception as exc:
            LOG.exception('Level dump failed')
            report.update(state='failed', error=str(exc))
            title, body = 'Level dump failed', str(exc)
        report['finished_at'] = timestamp()
        publish(directory / 'report.json', report)
        publish(self.output / 'latest.json', report | {'directory': str(directory)})
        LOG.info('%s — %s. Dump: %s', title, body, directory)
        if announce or report['state'] != 'complete':
            self.notify(title, f'{body}\n{directory.name}')
        return report['state'] == 'complete'
