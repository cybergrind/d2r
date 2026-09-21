"""Run with uv run -m inventory_tracking.osd [--demo]."""

import argparse
import math
import time
from pathlib import Path

from ..common import LOG, configure_logging, log_to_file
from ..probe import create_run
from .reader import LiveReader
from .state import State, display_lines


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be a finite positive number')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--demo', action='store_true', help='Preview 1526/1545 HP, 3 missing rejuvenations, 1 missing HP potion'
    )
    parser.add_argument('--text', action='store_true', help='Print state changes instead of opening a window')
    parser.add_argument('--once', action='store_true', help='Print one sample and exit (implies --text)')
    parser.add_argument(
        '--merc-heal',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Heal merc using healing_config.py thresholds; Shift+1/2/3/4',
    )
    parser.add_argument(
        '--player-heal',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Heal player using healing_config.py thresholds; keys 1/2/3/4',
    )
    parser.add_argument('--pid', type=int, help='Pin a game PID; omit to rediscover after restarts')
    parser.add_argument('--interval', type=positive_float, default=0.1, help='Delay between reads in seconds')
    parser.add_argument('--max-age', type=positive_float, default=2.0, help='Seconds before readings display as stale')
    parser.add_argument(
        '--rejuvenation-target',
        type=int,
        choices=range(17),
        default=None,
        metavar='0..16',
        help='Override automatic column target',
    )
    parser.add_argument(
        '--healing-target',
        type=int,
        choices=range(17),
        default=None,
        metavar='0..16',
        help='Override automatic column target',
    )
    parser.add_argument(
        '--x', type=int, default=0, help='Horizontal offset from center in logical pixels (positive = right)'
    )
    parser.add_argument(
        '--y', type=int, default=-130, help='Vertical offset from center in logical pixels (negative = up)'
    )
    parser.add_argument('--font-size', type=positive_float, default=16)
    parser.add_argument('--monitor', type=int, help='Zero-based monitor index; compositor default when omitted')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'runs' / 'osd')
    args = parser.parse_args()
    if args.monitor is not None and args.monitor < 0:
        parser.error('monitor must be nonnegative')
    if (args.rejuvenation_target or 0) + (args.healing_target or 0) > 16:
        parser.error('combined potion targets must fit the maximum 16 belt cells')
    configure_logging()
    directory, _ = create_run(args.output.resolve())
    with log_to_file(directory / 'osd.log'):
        LOG.info('OSD session: %s', directory)
        reader = None
        if args.demo:

            def latest():
                return State(time.monotonic(), 1526 * 256, 1545 * 256, 5, 7)
        else:
            reader = LiveReader(
                directory,
                pid=args.pid,
                interval=args.interval,
                merc_heal=args.merc_heal and not args.once,
                player_heal=args.player_heal and not args.once,
            )
            latest = reader.latest
            reader.start()
        try:
            if args.text or args.once:
                previous = None
                while True:
                    state = latest()
                    lines = display_lines(
                        state,
                        now=time.monotonic(),
                        max_age=args.max_age,
                        rejuvenation_target=args.rejuvenation_target,
                        healing_target=args.healing_target,
                    )
                    if lines != previous:
                        print(('PREVIEW · ' if args.demo else '') + ' · '.join(lines), flush=True)
                        previous = lines
                    if args.once and state.reason != 'connecting':
                        return 0 if state.current_raw is not None else 2
                    time.sleep(0.1)
            from .window import show

            return show(latest, args)
        except KeyboardInterrupt:
            return 0
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            LOG.error('Cannot display OSD: %s. Check that the native GTK4/layer-shell libraries are installed.', exc)
            return 1
        finally:
            if reader:
                reader.stop()


if __name__ == '__main__':
    raise SystemExit(main())
