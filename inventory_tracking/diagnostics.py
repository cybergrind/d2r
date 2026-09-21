"""Command-line interface for host probes and sandbox watchers."""

import argparse
from pathlib import Path

from .common import configure_logging
from .probe import probe
from .reports import watch


DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'runs'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='Shared output directory')
    commands = parser.add_subparsers(dest='command', required=True)
    probe_parser = commands.add_parser('probe', help='Run on host with D2R running; writes log and report')
    probe_parser.add_argument('--pid', type=int, help='Select one actual D2R.exe process')
    probe_parser.add_argument('--images', action='store_true', help='Also discover loaded PE image candidates')
    probe_parser.add_argument(
        '--units', action='store_true', help='Capture image and inspect candidate player/item units'
    )
    probe_parser.add_argument(
        '--capture', action='store_true', help='Discover and capture readable image ranges (64 MiB max)'
    )
    probe_parser.add_argument('--merc', action='store_true', help='Also research mercenary/monster health')
    watch_parser = commands.add_parser('watch', help='Wait inside sandbox for a host probe report')
    watch_parser.add_argument('--timeout', type=float, default=300)
    watch_parser.add_argument('--include-existing', action='store_true', help='Also accept already recorded runs')
    args = parser.parse_args()
    configure_logging()
    args.output = args.output.resolve()
    if args.command == 'watch':
        if args.timeout <= 0:
            parser.error('--timeout must be positive')
        return watch(args)
    return probe(args)
