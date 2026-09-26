"""Win+D host diagnostic: persist NPC grids and loaded stock without opening UI."""

import fcntl
import struct
import time
from pathlib import Path
from typing import Any

from inventory_tracking.appraisal.overlay import overlay_process
from inventory_tracking.appraisal.service import notify
from inventory_tracking.collection.capture import read_item_record, read_owner_grids
from inventory_tracking.common import configure_logging, log_to_file, timestamp
from inventory_tracking.hover.sampling import observe_ui
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader


OUTPUT = Path('inventory_tracking/runs/shop-probe')


def dump(pid, images, capture):
    snapshot = sample_units(pid, images, capture, merc=True)
    result: dict[str, Any] = {'snapshot': snapshot, 'owners': [], 'items': [], 'issues': []}
    if snapshot.get('status') != 'research':
        raise ValueError(snapshot.get('error', 'Unit snapshot unavailable'))
    items = snapshot['groups']['items']['units']
    with open(f'/proc/{pid}/mem', 'rb', buffering=0) as memory:
        reader = ResearchReader(memory.fileno(), process_mappings(pid))
        pointers = set()
        for unit in snapshot['groups']['monsters']['units']:
            owner = {key: unit[key] for key in ('address', 'unit_id', 'txt_id')}
            result['owners'].append(owner)
            try:
                owner['grids'] = read_owner_grids(reader.read, unit)
                pointers.update(p for grid in owner['grids'].values() for p in grid['cells'] if p)
            except (OSError, ValueError, struct.error) as exc:
                owner['error'] = str(exc)
        for unit in items:
            if unit['address'] not in pointers and unit.get('details', {}).get('owner_id') != 0xFFFFFFFF:
                continue
            try:
                result['items'].append(read_item_record(reader.read, unit, items))
            except (OSError, ValueError, struct.error) as exc:
                result['issues'].append(f'Item {unit["unit_id"]}: {exc}')
        result['bytes_requested'] = reader.bytes_requested
    try:
        result['ui'] = observe_ui(pid, images, snapshot, all_grids=True)
    except (OSError, ValueError) as exc:
        result['issues'].append(f'UI: {exc}')
    if identity(pid) != images['identity']:
        raise ValueError('Game process changed during dump')
    return result


def main():
    configure_logging()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / 'probe.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            notify('Shop dump already running', 'Wait for the completion notification.')
            return 1
        directory, report = create_run(OUTPUT)
        publish(directory / 'report.json', report)
        with log_to_file(directory / 'probe.log'):
            try:
                pid, images, capture = LiveReader(directory).connect(directory)
                result = dump(pid, images, capture)
                publish(directory / 'stock.json', result)
                count = sum(bool(o.get('grids')) for o in result['owners'])
                report.update(state='complete', owners_with_grids=count, items=len(result['items']))
                title = 'Shop dump saved'
                body = f'{count} NPC inventories, {len(result["items"])} item records. {directory.name}'
                notify(title, f'{count} NPC inventories, {len(result["items"])} item records. {directory.name}')
            except Exception as exc:
                report.update(state='failed', error=str(exc))
                title, body = 'Shop dump failed', str(exc)
                notify(title, body)
            finally:
                report['finished_at'] = timestamp()
                publish(directory / 'report.json', report)
                publish(OUTPUT / 'latest.json', report | {'directory': str(directory)})
        with overlay_process(directory, True) as display:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                publish(display, {'checked_at': time.monotonic(), 'lines': [title, body]})
                time.sleep(0.2)
        return 0 if report['state'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
