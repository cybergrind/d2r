"""Host-only controlled hover probe: ring, empty space, then ring again."""

import argparse
import json
import os
import re
import struct
import time
from pathlib import Path

from inventory_tracking.common import configure_logging, timestamp
from inventory_tracking.hover.legacy import capture_selection, read_indexed_hover, scan_hover
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader


def discover_hover(directory, capture):
    """Scan stable executable ranges from the existing sparse capture."""
    if 'blocks' not in capture:
        capture = json.loads((directory / 'capture.json').read_text())
    base = capture['base']
    with (directory / 'image.bin').open('rb') as stream:
        blocks = []
        for block in capture['blocks']:
            if not block.get('mapping_stable'):
                continue
            for section in capture['pe']['sections']:
                if not section['characteristics'] & 0x20000000:
                    continue
                start = max(block['address'], base + section['rva'])
                stop = min(block['address'] + block['size'], base + section['rva'] + section['virtual_size'])
                if start < stop:
                    stream.seek(block['file_offset'] + start - block['address'])
                    blocks.append((start, stream.read(stop - start)))
    candidates = scan_hover(sorted(blocks), base, capture['pe']['image_size'])
    if len(candidates) != 1:
        raise ValueError(f'Expected one hover candidate; found {candidates}')
    return candidates[0]


def discover_selector(directory, rva):
    capture = json.loads((directory / 'capture.json').read_text())
    pattern = re.compile(rb'\x8b\x0d....\x8b\xc1\x48\x03\xc0\xc6\x84\xc2....\x01\x48\x8b\x74', re.DOTALL)
    candidates = set()
    with (directory / 'image.bin').open('rb') as stream:
        for block in capture['blocks']:
            if not block.get('mapping_stable'):
                continue
            stream.seek(block['file_offset'])
            for match in pattern.finditer(stream.read(block['size'])):
                if struct.unpack_from('<I', match.group(), 14)[0] - 1 != rva:
                    continue
                address = block['address'] + match.start()
                executable = any(
                    section['characteristics'] & 0x20000000
                    and capture['base'] + section['rva'] <= address
                    and address + len(match.group()) <= capture['base'] + section['rva'] + section['virtual_size']
                    for section in capture['pe']['sections']
                )
                target = address + 6 + struct.unpack_from('<i', match.group(), 2)[0] - capture['base']
                if executable and 0 <= target <= capture['pe']['image_size'] - 4:
                    candidates.add(target)
    if len(candidates) != 1:
        raise ValueError(f'Expected one hover selector instruction, found {sorted(candidates)}')
    return candidates.pop()


def read_hover(pid, images, rva, selector_rva, observations):
    address = images['candidate_base'] + rva
    if identity(pid) != images['identity']:
        raise ValueError('Hover process changed')
    before = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, before).read
        observation = read_indexed_hover(read, address, images['candidate_base'] + selector_rva)
    finally:
        os.close(fd)
    after = process_mappings(pid)
    ranges = [(images['candidate_base'] + selector_rva, 4), (address + observation['slot'] * 16, 12)]
    if identity(pid) != images['identity'] or any(
        read_mappings(before, start, size) != read_mappings(after, start, size) for start, size in ranges
    ):
        raise ValueError('Hover process/mapping changed')
    observations.append(observation)
    return observation['hover']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('inventory_tracking/runs/hover-appraisal'))
    parser.add_argument('--pid', type=int)
    parser.add_argument('--delay', type=float, default=5)
    parser.add_argument('--interval', type=float, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.delay <= 60 or not 2 <= args.interval <= 60:
        parser.error('Delay must be 1..60 seconds; interval 2..60 seconds')
    configure_logging()
    directory, report = create_run(args.output)
    publish(directory / 'report.json', report)
    try:
        # connect() enforces the supported executable fingerprint; no live loop or input automation starts.
        pid, images, capture = LiveReader(directory, pid=args.pid).connect(directory)
        rva = discover_hover(directory, capture)
        selector_rva = discover_selector(directory, rva)
        report.update(hover_rva=rva, selector_rva=selector_rva, validated=False, samples=[])
        print(f'Candidate RVA {rva:#x}; output {directory}', flush=True)
        for number, label in enumerate(('ring', 'empty', 'ring')):
            pause = args.delay if number == 0 else args.interval
            print(f'Hover {label}; sampling in {pause:g} seconds', flush=True)
            time.sleep(pause)
            observations = []
            result = capture_selection(
                lambda observations=observations: read_hover(pid, images, rva, selector_rva, observations),
                lambda: sample_units(pid, images, capture, item_class=537),
            )
            if len({row['slot'] for row in observations}) > 1:
                raise ValueError('Hover selector changed across item capture')
            result['raw_observations'] = observations
            publish(directory / f'sample-{number}.json', result)
            summary = {key: value for key, value in result.items() if key not in ('snapshot', 'item')}
            summary.update(
                expected=label, file=f'sample-{number}.json', item_class=result.get('item', {}).get('txt_id')
            )
            report['samples'].append(summary)
            publish(directory / 'report.json', report)
            print(json.dumps(summary), flush=True)
        first, empty, last = report['samples']
        matched = (
            first['status'] == last['status'] == 'candidate'
            and first['item_class'] == last['item_class'] == 537
            and first['hover'] == last['hover']
            and empty['hover'] is None
        )
        report.update(
            state='complete' if matched else 'blocked', exit_code=0 if matched else 2, sequence_matched=matched
        )
    except (Exception, KeyboardInterrupt) as exc:
        report.update(state='failed', error=str(exc), exit_code=1)
    report['finished_at'] = timestamp()
    publish(directory / 'report.json', report)
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
