"""The regression harness (combat/plan.md, the steer of 2026-10-10): every take through the
calibration gate and the policies, one scoreboard.

`combat gate [takes directory]` cuts each take that holds full casts, replays its recorded casts
(the gate: sim/engine.py `gate`, `verdict`) and runs the candidates of sim/policy.py on it, and
writes `scoreboard.json` beside the takes: per take whether it was fitted on or held out
(data/damage.json `fit_takes`), the gate's numbers and why it fails if it does, each candidate's
gain over the recorded casts; then the totals and what changed since the scoreboard before it. The
numbers a model change moves are read off one file instead of this plan's tables.
"""

import json
import statistics
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.damage import fit_takes
from inventory_tracking.combat.sim.engine import gate, score, simulate
from inventory_tracking.combat.sim.policy import MODES, compare
from inventory_tracking.combat.sim.situation import Situation, cut, describe
from inventory_tracking.combat.takes import Take


SCOREBOARD = 'scoreboard.json'
LEAST_CASTS = 5  # a take with fewer full casts says nothing of the model


def row(situation: Situation, *, policies: bool = True) -> dict[str, Any]:
    """One take's line: the gate on its recorded casts and, with `policies`, each candidate's gain."""
    found: dict[str, Any] = {'situation': describe(situation)}
    if policies:
        report = compare(situation)
        found['gate'] = report['manual']['gate']
        found['manual'] = report['manual']['score']['placement_per_combat_second']
        found['policies'] = {
            mode: {
                'gain': report[mode]['gain'],
                'casts': report[mode]['casts'],
                'casts_while_recorded_running': report[mode]['casts_while_recorded_running'],
            }
            for mode in MODES
        }
    else:
        outcome = simulate(situation, [(c.frame, c.fitted) for c in situation.casts])
        found['gate'] = gate(situation, outcome)
        found['manual'] = score(situation, outcome)['damage_per_second']
    found['passes'] = not found['gate']['fails']
    return found


def totals(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scored = {name: found for name, found in rows.items() if 'gate' in found}
    summary: dict[str, Any] = {'takes': len(scored), 'passing': sum(found['passes'] for found in scored.values())}
    for side in ('fit', 'holdout', 'unknown'):
        mine = [found for found in scored.values() if found['side'] == side]
        summary[side] = {'takes': len(mine), 'passing': sum(found['passes'] for found in mine)}
    for mode in MODES:
        gains = [f['policies'][mode]['gain'] for f in scored.values() if f['passes'] and 'policies' in f]
        gains = [gain for gain in gains if gain is not None]
        summary[f'{mode}_gain_on_passing'] = (
            {'median': round(statistics.median(gains), 3), 'least': min(gains), 'most': max(gains)} if gains else None
        )
    return summary


def changes(before: dict[str, Any] | None, rows: dict[str, dict[str, Any]]) -> list[str]:
    """What moved since the scoreboard before: takes that began or stopped passing, yield gains that
    moved by two points or more."""
    if not before:
        return []
    found = []
    for name, now in rows.items():
        was = before.get('takes', {}).get(name)
        if was is None or 'gate' not in was or 'gate' not in now:
            continue
        if was['passes'] != now['passes']:
            found.append(
                f'{name}: {"passes now" if now["passes"] else "fails now: " + "; ".join(now["gate"]["fails"])}'
            )
        old = was.get('policies', {}).get('yield', {}).get('gain')
        new = now.get('policies', {}).get('yield', {}).get('gain')
        if old is not None and new is not None and abs(new - old) >= 0.02:
            found.append(f'{name}: yield gain {old:+.0%} -> {new:+.0%}')
    return found


def build(directory: Path, *, policies: bool = True, write: bool = True) -> dict[str, Any]:
    fitted = fit_takes()
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(
        p for p in directory.iterdir() if (p / 'frames.jsonl').exists() or (p / 'frames.jsonl.gz').exists()
    ):
        take = Take.load(path)
        situation = cut(take)
        if len(situation.casts) < LEAST_CASTS:
            rows[path.name] = {'skipped': f'{len(situation.casts)} full casts'}
            continue
        # By the recording, not the directory: a trimmed or renamed fit take is still a fit take, and a
        # take that does not say where it came from is on neither side.
        side = 'unknown' if take.recording is None else 'fit' if take.recording in fitted else 'holdout'
        rows[path.name] = {'side': side, **row(situation, policies=policies)}
    target = directory / SCOREBOARD
    before = json.loads(target.read_text()) if target.exists() else None
    board = {'takes': rows, 'totals': totals(rows), 'changes': changes(before, rows)}
    if write:
        target.write_text(json.dumps(board, indent=1))
    return board


def lines(board: dict[str, Any]) -> list[str]:
    """The scoreboard as a table for the terminal."""
    out = []
    for name, found in board['takes'].items():
        if 'gate' not in found:
            out.append(f'{name:24} skipped ({found["skipped"]})')
            continue
        g, away = found['gate'], found['gate']['life_curves']['away']
        explained = g['life_explained_at_recorded_kill']
        gains = ' '.join(
            f'{mode} {p["gain"]:+.0%}' for mode, p in found.get('policies', {}).items() if p['gain'] is not None
        )
        out.append(
            f'{name:24} {found["side"]:7} {"pass" if found["passes"] else "FAIL":4} '
            f'explained {explained["median"]}/{explained["mean"]} ratio {g["damage_ratio"]} '
            f'bias {away["bias"]} (+{away["ahead"]} -{away["behind"]}, {away["monsters"]}) | {gains}'
            + ('' if found['passes'] else f' | {"; ".join(g["fails"])}')
        )
    out.append(json.dumps(board['totals']))
    out.extend(f'changed: {change}' for change in board['changes'])
    return out
