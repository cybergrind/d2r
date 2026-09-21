"""Persist a sparse image capture for offline location research."""

import hashlib
import os
from typing import Any

from .capture import MAX_CAPTURE, capture_ranges, scan_unit_table
from .common import LOG
from .image_probe import read_mappings
from .images import read_pe
from .linux_process import identity, process_mappings
from .reports import publish


def capture_image(pid, images, directory) -> dict[str, Any]:
    token = images['identity']
    base = images['candidate_base']
    pe = next(x['pe'] for x in images['images'] if x['base'] == base)
    if pe['image_size'] > MAX_CAPTURE:
        raise ValueError('Declared image exceeds capture limit')
    if identity(pid) != token:
        return {'status': 'stale', 'error': 'Process changed before capture'}
    before = process_mappings(pid)
    end = base + pe['image_size']
    ranges = [
        (max(base, m['start']), min(end, m['end']))
        for m in before
        if m['permissions'].startswith('r') and m['start'] < end and m['end'] > base
    ]
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        if identity(pid) != token or read_pe(lambda offset, size: os.pread(fd, size, base + offset)) != pe:
            return {'status': 'stale', 'error': 'Process or PE headers changed before capture'}
        path = directory / 'image.bin'
        with path.open('xb') as stream:
            path.chmod(0o600)
            result = capture_ranges(lambda address, size: os.pread(fd, size, address), ranges, stream)
        after = process_mappings(pid)
        result.update(
            status='captured',
            base=base,
            pe=pe,
            identity=token,
            file='image.bin',
            atomic_snapshot=False,
            mappings=[m for m in before if m['start'] < end and m['end'] > base],
        )
        for block in result['blocks']:
            address, size = block['address'], block['size']
            block['mapping_stable'] = read_mappings(before, address, size) == read_mappings(after, address, size)
        if identity(pid) != token or read_pe(lambda offset, size: os.pread(fd, size, base + offset)) != pe:
            result['status'] = 'stale'
        with path.open('rb') as stream:
            result['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()

            def code_blocks():
                for block in result['blocks']:
                    if not block['mapping_stable']:
                        continue
                    # Scan only declared executable sections, never invent bytes in gaps.
                    for section in pe['sections']:
                        if not section['characteristics'] & 0x20000000:
                            continue
                        start = max(block['address'], base + section['rva'])
                        stop = min(block['address'] + block['size'], base + section['rva'] + section['virtual_size'])
                        if start < stop:
                            stream.seek(block['file_offset'] + start - block['address'])
                            yield start, stream.read(stop - start)

            result['unit_table_candidates'] = (
                scan_unit_table(code_blocks(), base, pe['image_size']) if result['status'] != 'stale' else []
            )
    finally:
        os.close(fd)
    publish(directory / 'capture.json', result)
    LOG.info(
        'Captured %s bytes; %s signature candidates; status=%s',
        result['bytes_read'],
        len(result['unit_table_candidates']),
        result['status'],
    )
    return {k: v for k, v in result.items() if k not in ('blocks', 'mappings', 'pe')} | {'manifest': 'capture.json'}
