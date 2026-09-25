"""Collect the current character's items into the collection database, or query it."""

import argparse
from pathlib import Path
from typing import Any

from inventory_tracking.collection.capture import collect_inventory
from inventory_tracking.collection.export import DEFAULT_HTML, export_html
from inventory_tracking.collection.probe import probe_materials
from inventory_tracking.collection.service import DEFAULT_OUTPUT, record_collection
from inventory_tracking.collection.store import DEFAULT_DATABASE, CollectionStore
from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader


def collect_once(args) -> int:
    """Attach to the running game, read every owned item once and record the capture."""
    directory, created = create_run(args.output)
    report: dict[str, Any] = dict(created)
    publish(directory / 'report.json', report)
    try:
        with log_to_file(directory / 'probe.log'):
            reader = LiveReader(directory, pid=args.pid)
            pid, images, capture = reader.connect(directory)
            record = collect_inventory(pid, images, capture)
            build, summary = record_collection(directory, report, record, args.database, args.html)
            print(f'{build.character.name} ({build.character.class_name}, level {build.character.level}): {summary}')
            print(f'Shared tabs (owner unit → tab): {build.tabs}')
            timing = record['timing']
            print(f'Read {timing["bytes_requested"]} bytes in {timing["ms"]} ms; area {record["location"]}')
            for issue in build.issues:
                print(f'  issue: {issue}')
            print(f'Report: {directory}')
            return 0 if not build.issues else 2
    except Exception as exc:
        report.update(state='failed', error=str(exc), finished_at=timestamp())
        LOG.error('Collection failed: %s', exc)
        print(f'Collection failed: {exc}. Report: {directory}')
        return 1
    finally:
        publish(directory / 'report.json', report)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='inventory_tracking.collection')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    commands = parser.add_subparsers(dest='command', required=True)
    collect = commands.add_parser('collect', help='read every owned item from the running game once (host)')
    collect.add_argument('--pid', type=int)
    collect.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    collect.add_argument('--html', type=Path, default=DEFAULT_HTML, help='page to regenerate after the capture')
    commands.add_parser('status', help='row counts per table')
    probe = commands.add_parser('probe-materials', help='research: dump raw records of the currency/materials stash')
    probe.add_argument('--pid', type=int)
    probe.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    space = commands.add_parser('space', help='free cells per container; --fits WxH keeps only grids with room')
    space.add_argument('--fits', help='item size such as 2x4; sorted by how many still fit')
    export = commands.add_parser('export', help='write the searchable single-file HTML')
    export.add_argument('--html', type=Path, default=DEFAULT_HTML)
    query = commands.add_parser('query', help='search open placements')
    query.add_argument('text', nargs='*', help='words matched against name, set, runeword, sockets and stats')
    query.add_argument('--owner', help="character name or 'shared'")
    query.add_argument('--container', choices=('inventory', 'cube', 'equipped', 'mercenary', 'stash', 'shared_stash'))
    query.add_argument('--sockets', help="socket count or 'empty'")
    args = parser.parse_args(argv)
    if args.command == 'collect':
        configure_logging()
        return collect_once(args)
    if args.command == 'probe-materials':
        configure_logging()
        directory, report = create_run(args.output)
        try:
            with log_to_file(directory / 'probe.log'):
                pid, images, capture = LiveReader(directory, pid=args.pid).connect(directory)
                result = probe_materials(pid, images, capture)
                publish(directory / 'materials-probe.json', result)
                report.update(state='complete', finished_at=timestamp(), materials=len(result['materials']))
                print(f'{len(result["materials"])} material units, {len(result["owners"])} owners → {directory}')
                return 0
        except Exception as exc:
            report.update(state='failed', error=str(exc), finished_at=timestamp())
            print(f'Probe failed: {exc}. Report: {directory}')
            return 1
        finally:
            publish(directory / 'report.json', report)
    if args.command == 'status' and not args.database.exists():
        print(f'No collection database at {args.database}')
        return 2
    with CollectionStore(args.database) as store:
        if args.command == 'export':
            payload = export_html(store, args.html)
            print(f'{len(payload["rows"])} items → {args.html}')
            return 0
        if args.command == 'space':
            spaces = store.spaces(fits=args.fits)
            if args.fits:
                spaces.sort(key=lambda s: -s.fits.get(args.fits, 0))
            for s in spaces:
                where = s.container + (f' {s.tab}' if s.tab is not None else '')
                fits = ', '.join(f'{k}: {v}' for k, v in s.fits.items() if v)
                print(f'{s.owner:16s} {where:16s} free {s.free:3d}/{s.width * s.height:3d}   fits {fits or "nothing"}')
            return 0 if spaces else 1
        if args.command == 'status':
            for name, value in store.counts().items():
                print(f'{name}: {value}')
            for character in store.characters():
                print(
                    f'character: {character.name} ({character.class_name or "class unknown"}, level {character.level})'
                )
            return 0
        rows = store.query(' '.join(args.text), owner=args.owner, container=args.container, sockets=args.sockets)
        for item, placement in rows:
            extra = [f'{item.sockets} sockets' if item.sockets else '', item.set_name or '', item.runeword or '']
            print(f'{item.name} [{item.base_name}] — {placement.location.label}  {" · ".join(e for e in extra if e)}')
            for line in item.stat_lines:
                print(f'    {line}')
        print(f'{len(rows)} placements')
        return 0 if rows else 1


if __name__ == '__main__':
    raise SystemExit(main())
