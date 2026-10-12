"""Combat takes (combat/plan.md): `replay` prints a take's timeline, `analyse` its play metrics,
`trim` cuts a take to a range of frames. What is a build's own of a take (its attack emulated against
the record, its simulator and the gate over the takes) is that build's command: for the Echoing
Strike Warlock `python -m inventory_tracking.builds.warlock.echoing_strike` (`validate`, `calibrate`,
`simulate`, `inputs`, `policy`, `gate`, `compare`)."""

import argparse
import json
from pathlib import Path

from inventory_tracking.combat.analysis import write_analysis
from inventory_tracking.combat.takes import Take, timeline, trim


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('replay', 'analyse', 'trim'))
    parser.add_argument('take', type=Path, help='a take directory under runs/combat')
    parser.add_argument('--every', type=float, default=5.0, help='replay: seconds between timeline lines')
    parser.add_argument('--frames', type=int, nargs=2, help='trim: the first and last frame numbers')
    parser.add_argument('--to', type=Path, help='trim: the directory of the trimmed take')
    args = parser.parse_args(argv)
    if args.command == 'analyse':
        print(json.dumps(write_analysis(args.take), indent=1))
        return 0
    take = Take.load(args.take)
    if args.command == 'trim':
        print(trim(take, args.frames[0], args.frames[1], args.to))
        return 0
    print(json.dumps(take.summary(), indent=1, sort_keys=True))
    for line in timeline(take, every=args.every):
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
