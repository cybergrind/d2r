"""How much of the takes is kept: every level is recorded (user, 2026-10-12: "maybe we can retire some very old or
have some policy for how much do we keep"), so what is written has to stay small by itself.

A closed take is packed (`.jsonl` -> `.jsonl.gz`, lossless; the readers take either). Past `keep` bytes in all the
oldest takes go, a take with a death last; only recorder-named directories are touched. The recorder does both
when a take closes (takes/record.py), off its own thread.

    uv run --offline python -m inventory_tracking.takes.retain [--keep-gb N] [--dry-run] [directory]

packs every take under the directory (default: runs/combat) and removes what the limit says (`--dry-run`: reports).
"""

import argparse
import gzip
import shutil
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.takes.takes import RECORDING_NAME


GIGABYTE = 1024**3


def recordings(root: Path) -> list[Path]:
    """The takes under `root`, the oldest first (a recorder's directory name starts with its start time)."""
    found = [p for p in root.iterdir() if RECORDING_NAME.fullmatch(p.name) and (p / 'manifest.json').exists()]
    return sorted(found, key=lambda path: path.name)


def size(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.iterdir() if path.is_file())


def pack(directory: Path) -> int:
    """Gzip the take's `.jsonl` files in place; the bytes saved. A packed copy is checked to hold what
    the file holds before the file goes."""
    saved = 0
    for path in sorted(directory.glob('*.jsonl')):
        packed = path.with_name(path.name + '.gz')
        with path.open('rb') as source, gzip.open(packed, 'wb', compresslevel=6) as target:
            shutil.copyfileobj(source, target, 1 << 20)
        with path.open('rb') as source, gzip.open(packed, 'rb') as copy:
            same = all(block == copy.read(len(block)) for block in iter(lambda: source.read(1 << 20), b''))
            same = same and not copy.read(1)
        if not same:
            packed.unlink()
            raise OSError(f'{packed}: the packed copy differs from {path.name}')
        saved += path.stat().st_size - packed.stat().st_size
        path.unlink()
    return saved


def died(directory: Path) -> bool:
    """Whether the character died in the take: a `hurt` that left nothing (takes since 2026-10-12)."""
    for name, opener in (('events.jsonl', open), ('events.jsonl.gz', gzip.open)):
        path = directory / name
        if path.exists():
            with opener(path, 'rt', encoding='utf-8') as handle:
                return any('"hurt"' in line and '"dead": true' in line for line in handle)
    return False


def over(root: Path, keep: int, spare: frozenset[str] = frozenset()) -> list[Path]:
    """The takes to remove so that those under `root` hold `keep` bytes at the most: the oldest first,
    those with a death only once no other is left. Those named in `spare` (the open take) stay."""
    takes = recordings(root)
    sizes = {take: size(take) for take in takes}
    excess = sum(sizes.values()) - keep
    if excess <= 0:
        return []
    deaths = {take for take in takes if died(take)}
    found = []
    for take in [*(t for t in takes if t not in deaths), *(t for t in takes if t in deaths)]:
        if excess <= 0:
            break
        if take.name not in spare:
            found.append(take)
            excess -= sizes[take]
    return found


def tidy(root: Path, closed: Path | None, keep: int, spare: frozenset[str] = frozenset()) -> None:
    """What the recorder does when a take closes: pack it, then hold the whole to `keep` bytes."""
    try:
        if closed is not None and closed.exists():
            pack(closed)
        for take in over(root, keep, spare):
            shutil.rmtree(take)
            LOG.info('Combat take %s removed: the takes are held to %.0f GB', take.name, keep / GIGABYTE)
    except OSError as exc:
        LOG.warning('Combat takes not tidied (%s)', exc)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Pack the takes and hold them to a size.')
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'runs' / 'combat')
    parser.add_argument('--keep-gb', type=float, default=None, help='remove the oldest takes past this size')
    parser.add_argument('--dry-run', action='store_true', help='say what would be removed, remove nothing')
    args = parser.parse_args(argv)
    # Only takes a recorder closed: one still open is being written to.
    takes = [take for take in recordings(args.root) if 'finished_at' in (take / 'manifest.json').read_text()]
    before = sum(size(take) for take in takes)
    saved = sum(pack(take) for take in takes)
    print(f'{len(takes)} takes, {before / GIGABYTE:.2f} GB; packing saved {saved / GIGABYTE:.2f} GB')
    if args.keep_gb is not None:
        gone = over(args.root, int(args.keep_gb * GIGABYTE))
        for take in gone:
            if not args.dry_run:
                shutil.rmtree(take)
        print(f'{len(gone)} takes {"would be " if args.dry_run else ""}removed to keep {args.keep_gb:g} GB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
