"""The Echoing Strike Warlock's combat takes (combat/plan.md): `validate` the Echoing Strike emulation's
error against a take's recorded blades, `calibrate` its hit model against the recorded life drops,
`simulate` the recorded casts through the simulator against the recorded kills (the stage 4
calibration gate), `inputs` the input model against the recorded casts, `policy` the cast policies
on a take, `gate` the scoreboard over a directory of takes, `compare` the macro's takes against the
manual ones. A take's timeline, its play metrics and trimming are any build's:
`python -m inventory_tracking.takes`."""

import argparse
import json
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.compare import compare as compare_takes, lines as compare_lines
from inventory_tracking.builds.warlock.echoing_strike.damage import (
    explosion_table,
    link_table,
    mana_numbers,
    mana_table,
)
from inventory_tracking.builds.warlock.echoing_strike.hits import calibrate
from inventory_tracking.builds.warlock.echoing_strike.scoreboard import build, lines
from inventory_tracking.builds.warlock.echoing_strike.sim.engine import fitted_mana, replay
from inventory_tracking.builds.warlock.echoing_strike.sim.input import validate_inputs
from inventory_tracking.builds.warlock.echoing_strike.sim.policy import LEAD, MODES, compare
from inventory_tracking.builds.warlock.echoing_strike.sim.situation import cut, describe
from inventory_tracking.builds.warlock.echoing_strike.validate import validate
from inventory_tracking.takes.takes import Take
from inventory_tracking.takes.timeline import longest_visit


def window(take: Take, area: int | None):
    """The whole take, or its longest stay in `area` when one is asked for (a take before 2026-10-10
    may come back to a level: one map and one monster level hold for one stay only)."""
    if area is None:
        return cut(take)
    stay = longest_visit(take.frames, area)
    if stay is None:
        raise SystemExit(f'no frames in area {area}')
    return cut(take, *stay, area=area)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'command',
        choices=(
            'validate',
            'calibrate',
            'simulate',
            'inputs',
            'policy',
            'gate',
            'compare',
        ),
    )
    parser.add_argument('take', type=Path, help='a take directory under runs/combat (gate: the directory of takes)')
    parser.add_argument('--radius', type=float, help="simulate: contact radius in units (default: the hit model's)")
    parser.add_argument('--share', type=float, help='simulate: Health Link share (default: data/damage.json)')
    parser.add_argument('--links', type=int, help='simulate: Health Link linked monsters')
    parser.add_argument('--blast', type=float, help='simulate: Hex Purge explosion points (0 turns it off)')
    parser.add_argument('--mana', help="policy: the mana pool, 0 for none, or 'fit' (regen from the recorded casts)")
    parser.add_argument(
        '--area',
        type=int,
        help='simulate/policy/inputs: the longest stay in this area (a take before 2026-10-10 may span levels)',
    )
    parser.add_argument('--quick', action='store_true', help='gate: the gate alone, no policies')
    args = parser.parse_args(argv)
    if args.command == 'compare':
        print('\n'.join(compare_lines(compare_takes(args.take))))
        return 0
    if args.command == 'gate':
        print('\n'.join(lines(build(args.take, policies=not args.quick))))
        return 0
    take = Take.load(args.take)
    if args.command == 'inputs':
        print(json.dumps(validate_inputs(take, window(take, args.area)), indent=1))
        return 0
    if args.command == 'policy':
        situation = window(take, args.area)
        options = {}
        pool, regen, cost = mana_numbers()
        if args.mana == 'fit':
            options['mana'] = fitted_mana(situation, pool, cost)
        elif args.mana is not None:
            wanted = float(args.mana)
            options['mana'] = (wanted, wanted / (pool / regen) if pool and regen and wanted else 0.0, cost)
        modes = (*MODES, LEAD) if situation.routes else MODES  # a take with path records: the lead too
        report = compare(situation, modes, **options)
        report['mana_model'] = options.get('mana', mana_table())
        print(json.dumps(report, indent=1))
        return 0
    if args.command == 'simulate':
        situation = window(take, args.area)
        options: dict = {}
        if args.radius is not None:
            options['radius'] = args.radius
        if args.share is not None or args.links is not None:
            link_range, links, share = link_table()
            links = args.links if args.links is not None else links
            options['link'] = (link_range, links, args.share if args.share is not None else share)
        if args.blast is not None:
            options['explosion'] = (explosion_table()[0], args.blast)
        report = {'situation': describe(situation), 'options': options}
        report.update(fitted=replay(situation, 'fitted', **options), pointer=replay(situation, 'pointer', **options))
        print(json.dumps(report, indent=1))
        return 0
    if args.command == 'calibrate':
        print(json.dumps(calibrate(take), indent=1))
        return 0
    rect = next((f['rect'] for f in take.frames if f.get('rect')), [0, 0, 2560, 1418])
    txt_ids = {m['unit_id']: m['txt_id'] for m in take.missiles}
    print(json.dumps(validate(take.frames, rect, txt_ids), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
