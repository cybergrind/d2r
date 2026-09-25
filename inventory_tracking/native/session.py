"""Process selection, identity, memory-access and build diagnostics."""

import json
import os
import platform
from typing import Any

from inventory_tracking.common import LOG, error, read_text
from inventory_tracking.native.memory import proc_read, vm_read
from inventory_tracking.native.process import (
    find_game_processes,
    fingerprint_executable,
    identity,
    is_game,
    mapping_summary,
    process_info,
    process_mappings,
    select_readable_mapping,
)


class GameProcessUnavailable(RuntimeError):
    """No D2R.exe is running yet; callers may wait and retry."""


def select_game_process(requested_pid):
    if requested_pid is not None:
        if not is_game(requested_pid):
            raise RuntimeError(f'PID {requested_pid} is not identifiable as D2R.exe via argv[0]')
        return requested_pid
    candidates = find_game_processes()
    if not candidates:
        raise GameProcessUnavailable('Expected one D2R.exe process, found []; start the game or select --pid')
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one D2R.exe process, found {candidates}; run on host or select --pid')
    return candidates[0]


def inspect_game(pid) -> dict[str, Any]:
    result = process_info(pid)
    LOG.info('Game process: %s', json.dumps(result))
    try:
        mappings = process_mappings(pid)
    except OSError as exc:
        result['maps'] = error(exc)
        return result
    result['mapping_summary'] = mapping_summary(mappings)
    mapping = select_readable_mapping(mappings)
    if mapping is None:
        result['error'] = 'No suitable readable mapping found; no memory probe attempted'
        return result
    if identity(pid) != result['identity']:
        raise RuntimeError('Process identity changed before memory probe')

    address = mapping['start']
    size = min(16, mapping['end'] - address)
    result['probe_address'] = hex(address)
    result['probe_mapping'] = mapping
    result['process_vm_readv'] = vm_read(pid, address, size)
    result['proc_mem'] = proc_read(pid, address, size)
    stable_after_reads = identity(pid) == result['identity']
    result['executable_fingerprint'] = fingerprint_executable(pid, mappings)
    result['identity_stable'] = stable_after_reads and identity(pid) == result['identity']
    result['memory_access'] = result['identity_stable'] and any(
        result[method].get('ok', False) for method in ('process_vm_readv', 'proc_mem')
    )
    return result


def reader_environment():
    reader = {
        'reader': process_info(os.getpid()),
        'kernel': platform.release(),
        'ptrace_scope': read_text('/proc/sys/kernel/yama/ptrace_scope'),
    }
    LOG.info('Reader environment: %s', json.dumps(reader))
    return reader
