"""High-level host diagnostic workflow."""

import json
import os
import platform
import uuid
from datetime import UTC, datetime

from .common import LOG, error, log_to_file, read_text, timestamp
from .linux_process import (
    find_game_processes,
    fingerprint_executable,
    identity,
    is_game,
    mapping_summary,
    process_info,
    process_mappings,
    select_readable_mapping,
)
from .memory import proc_read, vm_read
from .reports import publish


def select_game_process(requested_pid):
    if requested_pid is not None:
        if not is_game(requested_pid):
            raise RuntimeError(f'PID {requested_pid} is not identifiable as D2R.exe via argv[0]')
        return requested_pid
    candidates = find_game_processes()
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one D2R.exe process, found {candidates}; run on host or select --pid')
    return candidates[0]


def inspect_game(pid):
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


def create_run(output):
    run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    directory = output / run_id
    directory.mkdir(parents=True)
    report = {
        'schema_version': 1,
        'run_id': run_id,
        'started_at': timestamp(),
        'state': 'running',
        'log': 'probe.log',
        'host': platform.node(),
        'reader_pid': os.getpid(),
    }
    return directory, report


def run_diagnostics(report, requested_pid):
    try:
        report.update(reader_environment())
        pid = select_game_process(requested_pid)
        report['game'] = inspect_game(pid)
        access = report['game'].get('memory_access', False)
        report['state'] = 'complete' if access else 'blocked'
        report['exit_code'] = 0 if access else 2
        LOG.info('Game diagnostic result: %s', json.dumps(report['game']))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(state='failed', error=error(exc), exit_code=1)
        LOG.exception('Probe failed')
    report['finished_at'] = timestamp()
    LOG.info('Finished: state=%s exit_code=%s', report['state'], report['exit_code'])


def probe(args):
    directory, report = create_run(args.output)
    with log_to_file(directory / 'probe.log'):
        publish(directory / 'report.json', report)
        LOG.info('Started run %s; output %s', report['run_id'], directory)
        run_diagnostics(report, args.pid)
        publish(directory / 'report.json', report)
    return report['exit_code']
