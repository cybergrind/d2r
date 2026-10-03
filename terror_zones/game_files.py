"""Read files out of the installed game's data (Steam D2R "static container"), read-only.

Layout seen 2026-10-02 in <install>/data: `.build.config` names the TVFS manifest (`vfs-1`), and
`NN-XXXXXXXX.data` files hold the encoded files back to back, no index files. A 16-byte key is
its own address (`key-layout-0 = 8 8 40 1`): 9 hash bytes, then the file's NN, its XXXXXXXX
number and a 40-bit offset. Encoded files are BLTE (chunks 'N' raw / 'Z' zlib) or plain zlib
(the manifest). TVFS table layout follows CascLib's CascRootFile_TVFS.cpp.

    uv run --offline python -m terror_zones.game_files <install> data/hd/global/excel/desecratedzones.json -o out.json
    uv run --offline python -m terror_zones.game_files <install> --list excel/
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path


Entry = tuple[bytes, int, int]  # key, encoded size, content size

FOLDER = 0x80000000
HASH_BYTES = 9


def location(key: bytes) -> tuple[str, int]:
    """(data file name, offset) a key points at."""
    folder, archive = key[HASH_BYTES], key[HASH_BYTES + 1]
    return f'{folder:02x}-{archive:08x}.data', int.from_bytes(key[HASH_BYTES + 2 : HASH_BYTES + 7], 'big')


def decode(raw: bytes) -> bytes:
    if raw[:4] != b'BLTE':
        return zlib.decompress(raw)
    header = struct.unpack_from('>I', raw, 4)[0]
    if header == 0:
        position, sizes = 8, [len(raw) - 8]
    else:
        count = int.from_bytes(raw[9:12], 'big')
        sizes = [struct.unpack_from('>I', raw, 12 + 24 * index)[0] for index in range(count)]
        position = 12 + 24 * count
    parts = []
    for size in sizes:
        block = raw[position : position + size]
        position += size
        if block[:1] == b'N':
            parts.append(block[1:])
        elif block[:1] == b'Z':
            parts.append(zlib.decompress(block[1:]))
        else:
            raise ValueError(f'Unsupported BLTE chunk mode {block[:1]!r}')
    return b''.join(parts)


def tvfs_files(table: bytes) -> dict[str, list[Entry]]:
    """Path -> its spans, from a decoded TVFS manifest."""
    if table[:4] != b'TVFS':
        raise ValueError('Not a TVFS manifest')
    key_size = table[6]
    _flags, paths, paths_size, vfs, _vfs_size, cft, cft_size = struct.unpack_from('>IIIIIII', table, 8)
    cft_width = 4 if cft_size > 0xFFFFFF else 3 if cft_size > 0xFFFF else 2 if cft_size > 0xFF else 1
    files: dict[str, list[Entry]] = {}

    def spans(offset) -> list[Entry]:
        position = vfs + offset
        count = table[position]
        position += 1
        found = []
        for _ in range(count):
            length = struct.unpack_from('>I', table, position + 4)[0]
            entry = cft + int.from_bytes(table[position + 8 : position + 8 + cft_width], 'big')
            position += 8 + cft_width
            found.append(
                (table[entry : entry + key_size], struct.unpack_from('>I', table, entry + key_size)[0], length)
            )
        return found

    def walk(position, end, prefix):
        # Name fragments accumulate until a node value closes them; a zero byte is a path separator.
        path = prefix
        while position < end:
            if table[position] == 0:
                path += '/' if path else ''
                position += 1
            if position < end and table[position] != 0xFF:
                length = table[position]
                path += table[position + 1 : position + 1 + length].decode('utf-8', errors='replace')
                position += 1 + length
            if position < end and table[position] == 0:
                path += '/'
                position += 1
            if position >= end:
                break
            if table[position] != 0xFF:
                path += '/'
                continue
            value = struct.unpack_from('>I', table, position + 1)[0]
            position += 5
            if value & FOLDER:
                size = (value & ~FOLDER) - 4
                walk(position, position + size, path)
                position += size
            else:
                files[path] = spans(value)
            path = prefix

    walk(paths, paths + paths_size, '')
    return files


class GameFiles:
    def __init__(self, install: Path):
        self.data = Path(install) / 'data'
        config = {}
        for line in (self.data / '.build.config').read_text().splitlines():
            if '=' in line:
                name, value = line.split('=', 1)
                config[name.strip()] = value.split()
        key, size = bytes.fromhex(config['vfs-1'][1]), int(config['vfs-1-size'][1])
        self.files = tvfs_files(decode(self._encoded(key, size)))

    def _encoded(self, key: bytes, size: int) -> bytes:
        name, offset = location(key)
        with (self.data / name).open('rb') as stream:
            stream.seek(offset)
            return stream.read(size)

    def read(self, path: str) -> bytes:
        content = b''.join(decode(self._encoded(key, size)) for key, size, _length in self.files[path])
        expected = sum(length for _key, _size, length in self.files[path])
        if len(content) != expected:
            raise ValueError(f'{path}: {len(content)} bytes decoded, manifest says {expected}')
        return content


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    parser.add_argument(
        'path', nargs='?', help='file inside the game data, e.g. data/hd/global/excel/desecratedzones.json'
    )
    parser.add_argument('--list', metavar='TEXT', help='print the paths containing TEXT')
    parser.add_argument('-o', '--output', type=Path, help='write the file here instead of stdout')
    args = parser.parse_args(argv)
    game = GameFiles(args.install)
    if args.list is not None:
        print('\n'.join(path for path in sorted(game.files) if args.list in path))
    if args.path:
        content = game.read(args.path)
        if args.output:
            args.output.write_bytes(content)
        else:
            sys.stdout.buffer.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
