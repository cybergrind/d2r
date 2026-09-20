"""Linux procfs discovery, identity and executable inspection."""

import hashlib
import os
from pathlib import Path

from .common import error, read_text


STATUS_KEYS = {'Name', 'Uid', 'Gid', 'PPid', 'TracerPid', 'NSpid', 'CapEff', 'CapBnd', 'NoNewPrivs', 'Seccomp'}
ENV_KEYS = {
    'WINEPREFIX',
    'STEAM_COMPAT_DATA_PATH',
    'STEAM_COMPAT_CLIENT_INSTALL_PATH',
    'SteamAppId',
    'SteamGameId',
    'XDG_SESSION_TYPE',
    'DISPLAY',
    'WAYLAND_DISPLAY',
}


def status(pid):
    value = read_text(f'/proc/{pid}/status')
    if isinstance(value, dict):
        return value
    return {
        key: value.strip()
        for line in value.splitlines()
        for key, _, value in [line.partition(':')]
        if key in STATUS_KEYS
    }


def identity(pid):
    # starttime is field 22; comm may contain spaces or closing parentheses.
    stat = Path(f'/proc/{pid}/stat').read_text()
    return {'pid': pid, 'start_ticks': stat.rsplit(')', 1)[1].split()[19]}


def executable_name(value):
    return value.replace('\\', '/').rsplit('/', 1)[-1].lower()


def is_game(pid):
    try:
        argv0 = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')
        # Match argv[0], never a launcher argument mentioning D2R.exe.
        return executable_name(argv0) == 'd2r.exe'
    except OSError:
        return False


def process_info(pid):
    base = Path(f'/proc/{pid}')
    result = {'identity': identity(pid), 'status': status(pid)}
    for name in ('exe', 'cwd', 'ns/user', 'ns/pid', 'ns/mnt'):
        try:
            result[name] = os.readlink(base / name)
        except OSError as exc:
            result[name] = error(exc)
    for name in ('uid_map', 'gid_map', 'cgroup'):
        result[name] = read_text(base / name)
    try:
        entries = (base / 'environ').read_bytes().decode(errors='replace').split('\0')
        result['environment'] = {k: v for entry in entries for k, _, v in [entry.partition('=')] if k in ENV_KEYS}
    except OSError as exc:
        result['environment'] = error(exc)
    return result


def find_game_processes():
    return sorted(int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() and is_game(int(p.name)))


def process_mappings(pid):
    mappings = []
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) >= 5:
            start, end = (int(value, 16) for value in fields[0].split('-'))
            mappings.append(
                {'start': start, 'end': end, 'permissions': fields[1], 'path': fields[5] if len(fields) == 6 else ''}
            )
    return mappings


def is_game_mapping(mapping):
    return executable_name(mapping['path'].removesuffix(' (deleted)')) == 'd2r.exe'


def select_readable_mapping(mappings):
    readable = [
        entry
        for entry in mappings
        if entry['permissions'].startswith('r') and not entry['path'].startswith(('[vvar', '[vsyscall'))
    ]
    # Prefer the game image, then ordinary executable mappings, then other readable pages.
    return (
        next((entry for entry in readable if is_game_mapping(entry)), None)
        or next((entry for entry in readable if 'x' in entry['permissions']), None)
        or next(iter(readable), None)
    )


def mapping_summary(mappings):
    return {
        'total': len(mappings),
        'anonymous': sum(not entry['path'] for entry in mappings),
        'named_paths': sorted({entry['path'] for entry in mappings if entry['path']})[:80],
        'named_paths_limit': 80,
        'game_mappings': [entry for entry in mappings if is_game_mapping(entry)],
    }


def fingerprint_executable(pid, mappings):
    mapping = next((entry for entry in mappings if is_game_mapping(entry)), None)
    if mapping:
        path = Path(f'/proc/{pid}/root') / mapping['path'].removesuffix(' (deleted)').lstrip('/')
        source = 'mapped game path'
    else:
        path = Path(f'/proc/{pid}/cwd/D2R.exe')
        source = 'D2R.exe in game working directory (disk candidate only)'
    try:
        with path.open('rb') as stream:
            return {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(), 'path': str(path), 'source': source}
    except OSError as exc:
        return error(exc)
