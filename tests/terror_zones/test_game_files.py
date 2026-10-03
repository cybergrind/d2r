"""Reading files out of the Steam D2R static container: TVFS manifest, key layout, BLTE chunks."""

import struct
import zlib

import pytest

from terror_zones.game_files import GameFiles, decode, location, tvfs_files


def blte(*chunks):
    """A BLTE blob; each chunk is (mode, payload) with mode b'N' (raw) or b'Z' (zlib)."""
    blocks = [mode + (zlib.compress(data) if mode == b'Z' else data) for mode, data in chunks]
    table = b''.join(
        struct.pack('>II', len(block), len(data)) + bytes(16) for block, (_, data) in zip(blocks, chunks, strict=True)
    )
    header = b'\x0f' + len(blocks).to_bytes(3, 'big') + table
    return b'BLTE' + struct.pack('>I', 8 + len(header)) + header + b''.join(blocks)


def ekey(folder, archive, offset, tag=1):
    return bytes([tag]) * 9 + bytes([folder, archive]) + offset.to_bytes(5, 'big')


def folder(body):
    return b'\xff' + struct.pack('>I', 0x80000000 | (len(body) + 4)) + body


def leaf(vfs_offset):
    return b'\xff' + struct.pack('>I', vfs_offset)


def tvfs(entries):
    """A manifest with data/a.txt and data/b.bin; `entries` = [(ekey, encoded size, content size)] in that order."""
    cft = b''.join(key + struct.pack('>I', size) for key, size, _ in entries)
    vfs = b''.join(
        b'\x01' + struct.pack('>II', 0, length) + bytes([20 * i]) for i, (_, _, length) in enumerate(entries)
    )
    paths = folder(b'\x04data\x00' + folder(b'\x05a.txt' + leaf(0) + b'\x01b' + folder(b'\x04.bin' + leaf(10))))
    header = 46
    offsets = (header, len(paths), header + len(paths), len(vfs), header + len(paths) + len(vfs), len(cft))
    return b'TVFS\x01\x2e\x10\x10' + struct.pack('>IIIIIII', 0x0A, *offsets) + bytes(10) + paths + vfs + cft


def test_blte_chunks_are_joined_and_plain_zlib_is_accepted():
    assert decode(blte((b'N', b'plain '), (b'Z', b'packed'))) == b'plain packed'
    assert decode(zlib.compress(b'manifest')) == b'manifest'


def test_unknown_blte_chunk_mode_is_refused():
    with pytest.raises(ValueError, match='BLTE'):
        decode(blte((b'E', b'encrypted')))


def test_a_key_names_its_data_file_and_offset():
    assert location(ekey(0x00, 0x10, 0x4FC69B)) == ('00-00000010.data', 0x4FC69B)
    assert location(ekey(0x17, 0x01, 5)) == ('17-00000001.data', 5)


def test_manifest_paths_join_folders_and_name_fragments():
    first, second = (ekey(0, 1, 0), 30, 5), (ekey(0, 1, 30), 40, 6)

    files = tvfs_files(tvfs([first, second]))

    assert files == {'data/a.txt': [(first[0], 30, 5)], 'data/b.bin': [(second[0], 40, 6)]}


def test_game_files_reads_a_file_through_the_build_config(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    a, b = blte((b'Z', b'hello')), blte((b'N', b'binary'))
    manifest = zlib.compress(tvfs([(ekey(0, 1, 0), len(a), 5), (ekey(0, 1, len(a)), len(b), 6)]))
    (data / '00-00000001.data').write_bytes(a + b)
    (data / '00-00000002.data').write_bytes(manifest)
    key = ekey(0, 2, 0, tag=9).hex()
    (data / '.build.config').write_text(
        f'# Static Build Configuration\n\nvfs-1 = {"ab" * 16} {key}\nvfs-1-size = 99 {len(manifest)}\n'
    )

    game = GameFiles(tmp_path)

    assert sorted(game.files) == ['data/a.txt', 'data/b.bin']
    assert (game.read('data/a.txt'), game.read('data/b.bin')) == (b'hello', b'binary')
    with pytest.raises(KeyError):
        game.read('data/missing')
