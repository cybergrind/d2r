"""Grow D2R-decrypted.exe: merge code pages that a memory image has decrypted. Read-only on the game.

    grow.py                 dump the running game and merge it (needs /proc/<pid>/mem: run it yourself)
    grow.py a.bin b.bin     merge saved dumps from dump.py
    grow.py --at 0x1402a77a0 ...   say whether these addresses are on decrypted pages

A page is decrypted when it differs from D2R.exe on disk. Pages never go back: a page already
decrypted in D2R-decrypted.exe is kept. Reopen the file in Binary Ninja after it grows.
"""

import os
import sys
from pathlib import Path


EXE = Path('/mnt/extra/1000/games/steam/steamapps/common/Diablo II Resurrected/D2R.exe')
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'pricing' / 'raw' / 're' / 'D2R-decrypted.exe'  # git-ignored, beside the dumps
BASE = 0x140000000
SIZE = 0x142789000 - BASE  # end of .reloc
TEXT_FILE, TEXT_SIZE, TEXT_RVA = 0x400, 0x15CB800, 0x1000
PAGE = 0x1000


def live_image() -> bytes:
    sys.path.insert(0, str(ROOT))
    from inventory_tracking.native.process import find_game_processes, process_mappings

    pid = find_game_processes()[0]
    image = bytearray(SIZE)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    for m in process_mappings(pid):
        start, end = max(m['start'], BASE), min(m['end'], BASE + SIZE)
        for page in range(start, end, 0x100000):
            n = min(0x100000, end - page)
            try:
                image[page - BASE : page - BASE + n] = os.pread(fd, n, page)
            except OSError as exc:
                print('unreadable', hex(page), exc)
    os.close(fd)
    return bytes(image)


def pages():
    return range(0, TEXT_SIZE, PAGE)


def main(argv: list[str]) -> None:
    disk = EXE.read_bytes()
    out = bytearray(OUT.read_bytes()) if OUT.exists() else bytearray(disk)
    if len(out) != len(disk) or out[:TEXT_FILE] != disk[:TEXT_FILE]:
        print('D2R.exe changed (game update?): starting over from the file on disk')
        out = bytearray(disk)

    def decrypted(page: int) -> bool:
        at = TEXT_FILE + page
        return out[at : at + PAGE] != disk[at : at + PAGE]

    if argv and argv[0] == '--at':
        for arg in argv[1:]:
            page = (int(arg, 16) - BASE - TEXT_RVA) & ~(PAGE - 1)
            print(arg, 'decrypted' if decrypted(page) else 'ENCRYPTED')
        return

    before = sum(decrypted(p) for p in pages())
    for name, image in [(a, Path(a).read_bytes()) for a in argv] or [('live game', live_image())]:
        added = []
        for page in pages():
            at = TEXT_FILE + page
            mem = image[TEXT_RVA + page : TEXT_RVA + page + len(disk[at : at + PAGE])]
            if not decrypted(page) and mem != disk[at : at + PAGE]:
                out[at : at + PAGE] = mem
                added.append(BASE + TEXT_RVA + page)
        print(f'{name}: +{len(added)} pages')
        # New pages as address runs: what the game ran for the first time during this session.
        runs: list[list[int]] = []
        for va in added:
            if runs and va == runs[-1][1]:
                runs[-1][1] = va + PAGE
            else:
                runs.append([va, va + PAGE])
        for start, end in runs:
            print(f'  {start:#x}-{end:#x}')
    after = sum(decrypted(p) for p in pages())
    if after != before or not OUT.exists():
        OUT.write_bytes(out)
    print(f'decrypted pages: {before} -> {after} of {len(pages())}')


if __name__ == '__main__':
    main(sys.argv[1:])
