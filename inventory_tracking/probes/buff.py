"""Host-only raw buff research: uv run -m inventory_tracking.probes.buff.

Candidate pointers are not interpreted as verified stat-list links or timers.
This recorder never enables an OSD warning or sends game input.
"""

import argparse
import json
import os
import struct
import time
from collections import deque
from pathlib import Path

from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.native.units import read_stats, unit_matches
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader
from inventory_tracking.tracking.state import from_research


def collect_candidates(read, root, *, max_nodes=64, readable=None):
    """Bounded neighborhood; retain raw bytes and provenance, including failed reads."""
    queue = deque([(root, 0)])
    seen = {root}
    blocks = []
    errors = []
    while queue and len(blocks) + len(errors) < max_nodes:
        address, depth = queue.popleft()
        try:
            raw = read(address, 0x1000 if depth == 0 else 0x100)
            blocks.append({'address': address, 'depth': depth, 'hex': raw.hex()})
        except (OSError, ValueError) as exc:
            errors.append({'address': address, 'reason': str(exc)})
            continue
        if depth >= 3:
            continue
        # Restrict discovery to the header: no recursive walk through state bits.
        for offset in range(0, 0x100, 8):
            pointer = struct.unpack_from('<Q', raw, offset)[0]
            if 0x10000 <= pointer < 2**47 and pointer % 8 == 0 and pointer not in seen:
                if readable is not None and not readable(pointer, 0x100):
                    continue
                seen.add(pointer)
                queue.append((pointer, depth + 1))
    return {'blocks': blocks, 'errors': errors, 'truncated': bool(queue)}


def collect_effect_lists(read, root, *, max_nodes=128):
    """Research two candidate list heads separately from the generic pointer walk.

    +0xD0 -> +0x68 links were observed in the captures; adjacent +0xC8 is
    a hypothesis. Raw fields are retained without asserting timer semantics.
    """
    result = {'complete': True, 'chains': [], 'nodes': [], 'errors': []}
    nodes = {}
    for head_offset in (0xC8, 0xD0):
        chain = {'head_offset': head_offset, 'addresses': []}
        result['chains'].append(chain)
        try:
            head = read(root + head_offset, 8)
            pointer = struct.unpack('<Q', head)[0]
            visited = set()
            while pointer:
                if pointer in visited:
                    raise ValueError('Effect list cycle')
                if pointer not in nodes and len(nodes) >= max_nodes:
                    raise ValueError('Effect list node limit')
                visited.add(pointer)
                chain['addresses'].append(pointer)
                if pointer not in nodes:
                    raw = read(pointer, 0xD0)
                    node = {'address': pointer, 'hex': raw.hex(), 'stats': read_stats(read, pointer + 0x30)}
                    nodes[pointer] = raw
                    result['nodes'].append(node)
                pointer = struct.unpack_from('<Q', nodes[pointer], 0x68)[0]
            if read(root + head_offset, 8) != head:
                raise ValueError('Effect list head changed')
        except (OSError, ValueError, struct.error) as exc:
            result['complete'] = False
            result['errors'].append({'head_offset': head_offset, 'reason': str(exc)})
    for address, raw in nodes.items():
        try:
            after = read(address, 0xD0)
            # Identity/state and links must agree. Timer fields may advance.
            if after[:0x24] != raw[:0x24] or after[0x68:0x80] != raw[0x68:0x80]:
                raise ValueError('Effect list identity or links changed')
        except (OSError, ValueError) as exc:
            result['complete'] = False
            result['errors'].append({'address': address, 'reason': str(exc)})
    return result


def capture_sample(pid, images, capture):
    snapshot = sample_units(pid, images, capture)
    state = from_research(snapshot) if 'groups' in snapshot else None
    if state is None or state.session is None:
        raise ValueError('No unambiguous, stable in-game player')
    player = next(p for p in snapshot['groups']['players']['units'] if p['unit_id'] == state.session.player_id)
    token = images['identity']
    mappings = process_mappings(pid)
    if identity(pid) != token:
        raise ValueError('Process changed before buff capture')
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, mappings)
        if not unit_matches(reader.read, player):
            raise ValueError('Player changed before buff capture')
        effects = collect_effect_lists(reader.read, player['stats_pointer'])

        def readable(address, size):
            return any(
                m['start'] <= address and address + size <= m['end'] and m['permissions'].startswith('r')
                for m in mappings
            )

        result = collect_candidates(reader.read, player['stats_pointer'], readable=readable)
        stable = unit_matches(reader.read, player) and identity(pid) == token and process_mappings(pid) == mappings
        return {
            'sample_monotonic': snapshot['sample_monotonic'],
            'finished_monotonic': time.monotonic(),
            'session': list(state.session),
            'player': player,
            'stable': stable,
            'validated': False,
            'atomic_snapshot': False,
            'effect_lists': effects,
            **result,
        }
    finally:
        os.close(fd)


def record(directory, report, *, seconds, pid=None):
    count = 0
    errors = 0
    report.update(samples_file='samples.jsonl', buff_probe_version=2)
    try:
        reader = LiveReader(directory, pid=pid)
        pid, images, capture = reader.connect(directory)
        report.update(identity=images['identity'], recording_started_at=timestamp())
        publish(directory / 'report.json', report)
        LOG.info('READY: recording. Return to game; leave Consume inactive for 10 seconds.')
        deadline = time.monotonic() + seconds
        with (directory / 'samples.jsonl').open('w', buffering=1) as output:
            while time.monotonic() < deadline:
                try:
                    sample = capture_sample(pid, images, capture)
                    count += 1
                except (OSError, ValueError) as exc:
                    sample = {'sample_monotonic': time.monotonic(), 'error': str(exc)}
                    errors += 1
                output.write(json.dumps(sample) + '\n')
                report.update(samples=count, errors=errors)
                publish(directory / 'report.json', report)
                time.sleep(1)
        report.update(state='complete', exit_code=0, stopped_by='time limit')
    except KeyboardInterrupt:
        report.update(state='complete' if count else 'failed', exit_code=0 if count else 1, stopped_by='user')
    except Exception as exc:
        LOG.exception('Buff recording failed')
        report.update(state='failed', exit_code=1, error=str(exc))
    if not count and report.get('state') == 'complete':
        report.update(state='failed', exit_code=1, error='No samples captured')
    report.update(samples=count, errors=errors, finished_at=timestamp())
    publish(directory / 'report.json', report)
    LOG.info('Recording %s: %s samples, %s errors. %s', report['state'], count, errors, directory)
    return report['exit_code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('inventory_tracking/runs/consume'))
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--pid', type=int)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('--seconds must be in 1..3600')
    configure_logging()
    directory, report = create_run(args.output.resolve())
    with log_to_file(directory / 'probe.log'):
        publish(directory / 'report.json', report)
        return record(directory, report, seconds=args.seconds, pid=args.pid)


if __name__ == '__main__':
    raise SystemExit(main())
