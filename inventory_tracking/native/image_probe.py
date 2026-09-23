"""Host workflow for matching loaded PE headers against the disk candidate."""

import hashlib
import os
from pathlib import Path

from inventory_tracking.common import error
from inventory_tracking.native.images import discover_images, read_pe
from inventory_tracking.native.process import identity, process_mappings


def disk_headers(fingerprint):
    path = fingerprint.get('path')
    if not path:
        return {'error': 'No disk executable available for matching'}, None
    try:
        with Path(path).open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()

            def read(offset, size):
                stream.seek(offset)
                return stream.read(size)

            pe = read_pe(read)
        if digest != fingerprint.get('sha256'):
            return {'error': 'Disk fingerprint changed since access probe'}, None
        return {'path': path, 'sha256': digest, 'pe': pe}, pe
    except (OSError, ValueError) as exc:
        return error(exc), None


def inspect_images(pid, game):
    token = game['identity']
    if identity(pid) != token:
        return {'status': 'stale', 'error': 'Process changed before image discovery'}
    disk, pe = disk_headers(game['executable_fingerprint'])
    mappings = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        if identity(pid) != token:
            return {'status': 'stale', 'error': 'Process changed while opening memory'}

        def read(address, size):
            return os.pread(fd, size, address)

        result = discover_images(read, mappings, pe)
    finally:
        os.close(fd)
    if identity(pid) != token:
        return {'status': 'stale', 'error': 'Process identity changed during image discovery'}
    after = process_mappings(pid)
    reads = [(image['base'], image['pe']['header_size']) for image in result['images']]
    for image in result['images']:
        if image['disk_header_match']:
            reads.append((image['base'] + image['pe']['entry_rva'], 1))
    if any(read_mappings(mappings, address, size) != read_mappings(after, address, size) for address, size in reads):
        result.pop('candidate_base', None)
        result.update(
            status='stale', error='Mappings covering parsed PE headers or entrypoints changed during discovery'
        )
    result['disk'] = disk
    result['identity'] = token
    return result


def read_mappings(mappings, address, size):
    """Compare only mapping portions used by a read, ignoring unrelated allocations.

    This is a before/after consistency check, not an atomic memory snapshot.
    """
    end = address + size
    return [
        (max(address, m['start']), min(end, m['end']), m['start'], m['permissions'], m['path'])
        for m in mappings
        if m['start'] < end and m['end'] > address
    ]
