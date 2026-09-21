"""Run with uv run -m inventory_tracking.osd [--demo]."""

import argparse
import math
import time
from dataclasses import replace
from pathlib import Path

from ..automation import Automation
from ..common import LOG, configure_logging, log_to_file
from ..config import MERC_HEALING, OSD, PLAYER_HEALING, READER
from ..heal import HealController
from ..models import State
from ..potion_input import PotionInput
from ..potion_ledger import PotionLedger
from ..potions import PotionsController
from ..probe import create_run
from ..reader import LiveReader
from .state import display_lines


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
        default=MERC_HEALING.enabled,
        help='Heal merc using config.py thresholds; Shift+1/2/3/4',
    )
    parser.add_argument(
        '--player-heal',
        action=argparse.BooleanOptionalAction,
        default=PLAYER_HEALING.enabled,
        help='Heal player using config.py thresholds; keys 1/2/3/4',
    )
    parser.add_argument('--pid', type=int, help='Pin a game PID; omit to rediscover after restarts')
    parser.add_argument(
        '--interval', type=positive_float, default=READER.interval, help='Delay between reads in seconds'
    )
    parser.add_argument(
        '--max-age', type=positive_float, default=OSD.max_age, help='Seconds before readings display as stale'
    )
    parser.add_argument(
        '--rejuvenation-target',
        type=int,
        choices=range(17),
        default=OSD.rejuvenation_target,
        metavar='0..16',
        help='Override automatic column target',
    )
    parser.add_argument(
        '--healing-target',
        type=int,
        choices=range(17),
        default=OSD.healing_target,
        metavar='0..16',
        help='Override automatic column target',
    )
    parser.add_argument(
        '--x', type=int, default=OSD.x, help='Horizontal offset from center in logical pixels (positive = right)'
    )
    parser.add_argument(
        '--y', type=int, default=OSD.y, help='Vertical offset from center in logical pixels (negative = up)'
    )
    parser.add_argument('--font-size', type=positive_float, default=OSD.font_size)
    parser.add_argument(
        '--monitor', type=int, default=OSD.monitor, help='Zero-based monitor index; compositor default when omitted'
    )
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'runs' / 'osd')
    args = parser.parse_args()
    try:
        osd_config = replace(
            OSD,
            **{
                name: getattr(args, name)
                for name in ('x', 'y', 'font_size', 'monitor', 'max_age', 'rejuvenation_target', 'healing_target')
            },
        )
        reader_config = replace(READER, interval=args.interval)
    except ValueError as exc:
        parser.error(str(exc))
    configure_logging()
    directory, _ = create_run(args.output.resolve())
    with log_to_file(directory / 'osd.log'):
        LOG.info('OSD session: %s', directory)
        reader = None
        if args.demo:

            def latest():
                return State(
                    time.monotonic(),
                    1526 * 256,
                    1545 * 256,
                    belt_contents=(531, 531, 606, 606) * 2 + (531, None, 606, 606) + (None, None, 606, None),
                )
        else:
            ledger = PotionLedger(directory.parent)
            deliver = PotionInput()
            configs = (
                replace(PLAYER_HEALING, enabled=args.player_heal and not args.once),
                replace(MERC_HEALING, enabled=args.merc_heal and not args.once),
            )
            automation = Automation(
                [HealController(config, PotionsController(config, ledger, deliver)) for config in configs]
            )
            reader = LiveReader(
                directory,
                pid=args.pid,
                config=reader_config,
                automation=automation,
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
                        config=osd_config,
                    )
                    if lines != previous:
                        print(('PREVIEW · ' if args.demo else '') + ' · '.join(lines), flush=True)
                        previous = lines
                    if args.once and state.reason != 'connecting':
                        return 0 if state.current_raw is not None else 2
                    time.sleep(osd_config.refresh_interval)
            from .window import show

            return show(latest, osd_config, demo=args.demo)
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
