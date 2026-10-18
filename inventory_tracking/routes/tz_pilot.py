"""Verify a one-game TZ probe log before promoting its arm to multiple games.

The receipt pins the log prefix ending at the successful TZ slice report. A
running service may append later lines without invalidating the evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from inventory_tracking.routes.tz_leveling import TOWER_GROUP_CORE, TOWER_GROUP_ITINERARY


CAVE = (3, 9, 13)
TARGETS = {
    CAVE: ((9, 'boss killed'), (13, 'chest opened')),
    TOWER_GROUP_ITINERARY: ((15, 'chest opened'), (25, 'boss killed')),
}
CREATE = re.compile(r'Macro: Creating ([A-Za-z0-9]+)')
AREAS = re.compile(r'TZ town memory: areas (\[[^]]+\]); effect (.+)')


def receipt_path(output: Path, itinerary: tuple[int, ...]) -> Path:
    """Keep each tested route's promotion separate from the service arm file."""
    if itinerary == CAVE:
        return output / 'tz-cave-pilot-receipt.json'
    if itinerary == TOWER_GROUP_ITINERARY:
        return output / 'tz-tower-pilot-receipt.json'
    raise ValueError('no pilot receipt path for this itinerary')


def _proof(raw: bytes, itinerary: tuple[int, ...]) -> tuple[int, dict[str, object]]:
    if itinerary not in TARGETS:
        raise ValueError('no pilot rule for this itinerary')
    lines = raw.splitlines(keepends=True)
    ends = [index for index, line in enumerate(lines) if b'TZ slice: maximum games reached;' in line]
    if len(ends) != 1:
        raise ValueError('one successful pilot end is required')
    end = ends[0]
    prefix = b''.join(lines[: end + 1])
    text = prefix.decode('utf-8')
    if text.count('TZ slice:') != 1 or 'TZ area action timed out' in text:
        raise ValueError('the pilot stopped or timed out before successful completion')
    games = CREATE.findall(text)
    if len(games) != 1:
        raise ValueError('one created game is required')
    required = set(itinerary)
    if itinerary == TOWER_GROUP_ITINERARY:
        reads = AREAS.findall(text)
        if len(reads) != 1:
            raise ValueError('one town memory TZ read is required')
        try:
            active = set(json.loads(reads[0][0]))
        except json.JSONDecodeError as error:
            raise ValueError('town TZ area list unreadable') from error
        if not TOWER_GROUP_CORE.issubset(active) or not reads[0][1].strip():
            raise ValueError('the Tower group was not confirmed in town memory')
        if 20 not in active:
            required.remove(20)  # its mandatory transit is not an active TZ area in this game
    for area in sorted(required):
        if f'TZ area {area}: travel observed' not in text or f'TZ area {area}: loot clear observed' not in text:
            raise ValueError(f'area {area} travel and loot completion not observed')
    for area, outcome in TARGETS[itinerary]:
        if f'TZ area {area}: {outcome} observed' not in text:
            raise ValueError(f'area {area} target outcome not observed')
    if re.search(r'TZ area \d+: (?:boss|chest|object) (?:failed|unreachable) observed', text):
        raise ValueError('a route target failed')
    facts: dict[str, object] = {
        'game': games[0],
        'completed_areas': sorted(required),
        'target_outcomes': [[area, outcome] for area, outcome in TARGETS[itinerary]],
    }
    return len(prefix), facts


def write_receipt(log: Path, receipt: Path, itinerary: tuple[int, ...]) -> None:
    """Persist a validated pilot log prefix, or raise without writing a receipt."""
    raw = log.read_bytes()
    size, facts = _proof(raw, itinerary)
    saved = {
        'version': 1,
        'log': str(log.resolve()),
        'prefix_bytes': size,
        'prefix_sha256': hashlib.sha256(raw[:size]).hexdigest(),
        'itinerary': list(itinerary),
        'facts': facts,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(receipt.suffix + '.tmp')
    temporary.write_text(json.dumps(saved, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(receipt)


def validated_receipt(receipt: Path, itinerary: tuple[int, ...]) -> bool:
    """Recheck the persisted receipt against the played log; never trust its fields alone."""
    try:
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if not isinstance(saved, dict) or set(saved) != {
            'version',
            'log',
            'prefix_bytes',
            'prefix_sha256',
            'itinerary',
            'facts',
        }:
            return False
        if saved['version'] != 1 or saved['itinerary'] != list(itinerary):
            return False
        size = saved['prefix_bytes']
        if type(size) is not int or size <= 0:
            return False
        raw = Path(saved['log']).read_bytes()[:size]
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != saved['prefix_sha256']:
            return False
        proven_size, facts = _proof(raw, itinerary)
        return proven_size == size and facts == saved['facts']
    except OSError, ValueError, TypeError, KeyError, UnicodeDecodeError:
        return False
