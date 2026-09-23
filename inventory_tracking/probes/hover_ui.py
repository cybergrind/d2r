"""Host-only UI-path capture: item A, empty inventory space, item B, item A."""

import argparse
import time
from pathlib import Path

from inventory_tracking.common import configure_logging, timestamp
from inventory_tracking.hover.sampling import capture_ui_sample, observe_ui
from inventory_tracking.hover.selection import resolve_selection
from inventory_tracking.native.unit_probe import sample_units
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('inventory_tracking/runs/hover-ui'))
    parser.add_argument('--pid', type=int)
    parser.add_argument('--scenario', choices=('sequence', 'controls', 'panels', 'mercenary'), default='sequence')
    parser.add_argument('--delay', type=float, default=5)
    parser.add_argument('--interval', type=float, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.delay <= 60 or not 2 <= args.interval <= 60:
        parser.error('Delay must be 1..60 seconds; interval 2..60 seconds')
    configure_logging()
    directory, report = create_run(args.output)
    report.update(validated=False, samples=[], probe_revision=5, scenario=args.scenario)
    publish(directory / 'report.json', report)
    try:
        pid, images, capture = LiveReader(directory, pid=args.pid).connect(directory)
        print(f'Output: {directory}. Keep inventory open; use two different items A and B.', flush=True)
        labels = (
            ('hover item A', 'hover empty inventory space', 'hover item B', 'hover item A')
            if args.scenario == 'sequence'
            else (
                'hover item A',
                'close inventory',
                'reopen inventory and hover A',
                'pick up A and hover B while holding A',
                'put A back and hover A',
            )
        )
        if args.scenario == 'panels':
            labels = (
                'hover equipped item A',
                'hover equipped item B',
                'open shop and hover vendor item A',
                'hover vendor item B',
            )
        if args.scenario == 'mercenary':
            labels = ('open mercenary inventory and hover equipped item A', 'hover mercenary equipped item B')
        include_monsters = args.scenario in ('panels', 'mercenary')
        for number, label in enumerate(labels):
            pause = args.delay if number == 0 else args.interval
            print(f'{label}; capture in {pause:g} seconds. Hold until CAPTURED.', flush=True)
            time.sleep(pause)
            result = capture_ui_sample(
                lambda: observe_ui(pid, images),
                lambda: sample_units(pid, images, capture, merc=include_monsters),
                lambda units: observe_ui(pid, images, units, all_grids=include_monsters),
            )
            result['expected'] = label
            result['selection'] = resolve_selection(result, images['candidate_base'])
            filename = f'sample-{number}.json'
            publish(directory / filename, result)
            report['samples'].append(
                {
                    'expected': label,
                    'file': filename,
                    'ui_path_stable': result['ui_path_stable'],
                    'selection': result['selection'],
                }
            )
            publish(directory / 'report.json', report)
            print(f'CAPTURED {label}; selection={result["selection"]["status"]}', flush=True)
        report.update(state='complete', exit_code=0)
    except (Exception, KeyboardInterrupt) as exc:
        report.update(state='failed', error=str(exc), exit_code=1)
    report['finished_at'] = timestamp()
    publish(directory / 'report.json', report)
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
