"""What the macro holds between its looks at the game, as a plain row for the combat recorder.

`snapshot` reads off a `MacroRunner`, without touching it, what a take's frames cannot say: attack mode, the routine,
the build, the route's progress, the level card's mark. Reads race the runner harmlessly (the next snapshot rights a
value caught mid-change). The recorder writes the row as a `state` event when a take opens and whenever it changes
(takes/record.py), so an incident can be replayed as it was.
"""

import math
import subprocess
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any


def route(progress: Any) -> dict[str, Any] | None:
    """The routes' progress in this game: the facts, and the stage each level entered is at."""
    if progress is None:
        return None
    facts = progress.facts
    found: dict[str, Any] = {
        'game': progress.game,
        'entered': sorted(facts.entered),
        'used': sorted([area, mark, list(place)] for area, mark, place in facts.used),
        'finished': sorted([area, mark] for area, mark in facts.finished),
        'stood': sorted([area, mark] for area, mark in facts.stood),
        'looted': sorted(facts.looted),
        'dead': None,
        'stages': {},
    }
    if progress.dead is not None:
        with suppress(Exception):
            found['dead'] = sorted(progress.dead())
    for area in sorted(facts.entered):
        with suppress(Exception):
            step = progress.step(area)
            if step is not None:
                stage = step.stage
                found['stages'][str(area)] = [step.route, stage.kind, stage.mark, stage.boss, stage.to, stage.pending]
    return found


def card(target: Any) -> list[Any] | None:
    """The mark the level card leads with, as the teleport step is given it."""
    if target is None:
        return None
    return [target.area, target.label, target.kind, list(target.point), target.use, target.warp]


def pursuit(hunter: Any) -> dict[str, Any]:
    """The active task with the pursuit loop on (macros/pursuit.py): the last decision's goal and the mailbox key with
    its press time (a time, not an age: an age would make every row differ)."""
    goal, posted = hunter.pursued, hunter.pursuit
    return {
        'goal': None
        if goal is None
        else {
            'label': goal.label,
            'do': goal.do,
            'place': [round(goal.place[0], 1), round(goal.place[1], 1)],
            'near': goal.near if goal.near != float('inf') else None,
            'unit': goal.unit,
            'known': goal.known,
        },
        'key': None if posted is None else posted.key,
        'pressed_at': None if posted is None else round(posted.pressed_at, 3),
        # the pickup key's run mode at the last look (macros/runmode.py): full clear or not, and why
        'run_mode': None if getattr(hunter, 'mode', None) is None else [hunter.mode.clear, hunter.mode.why],
    }


def when(at: float | None) -> float | None:
    """A clock time as written (the runner's clock is the recorder's, time.monotonic); None for never."""
    return None if at is None or not math.isfinite(at) else round(at, 3)


def times(found: dict[Any, float]) -> dict[str, float | None]:
    """{key: clock time} as written: the keys as text, in order."""
    return {str(key): when(at) for key, at in sorted(dict(found).items(), key=lambda item: str(item[0]))}


def memory(runner: Any) -> dict[str, Any]:
    """What the hunt and the runner remember between looks, as clock times, never ages (rca/2026-10-13/
    replay-readiness.md §6): the sweep, jumps and distrusted ways, buffs, monsters left alone, the pursuit's last
    judgement. A part that cannot be read is left out."""
    hunter: Any = getattr(runner, 'hunter', None)
    parts: dict[str, Callable[[], Any]] = {
        'quiet_until': lambda: when(runner.quiet_until),
        'attack_declined': lambda: bool(runner.attack_declined),
        'arrived': lambda: [runner.journey.area, runner.journey.last[0], when(runner.journey.last[1])],
        'sweep': lambda: {
            'until': when(hunter.sweep.until),
            'looked': when(hunter.sweep.looked),
            'fails': int(hunter.sweep.fails),
            'shunned': [[round(x, 1), round(y, 1), when(at)] for (x, y), at in list(hunter.sweep.shunned)],
        },
        'travel': lambda: {
            'warped_at': when(hunter.travel.warped_at),
            'jumped_at': times(hunter.travel.jumped_at),
            'jump_failed': times(hunter.travel.jump_failed),
            'distrusted': times(hunter.travel.distrusted),
        },
        'buffs': lambda: {
            'cast_at': sorted(
                ([skill, unit, when(at)] for (skill, unit), at in dict(hunter.buffs.cast_at).items()),
                key=lambda row: (row[0], row[1] is not None, row[1] or 0),
            ),
            'unseen': {str(skill): count for skill, count in sorted(dict(hunter.buffs.unseen).items())},
        },
        'untouchable': lambda: times(hunter.untouchable),
        'vanished': lambda: sorted(set(hunter.vanished)),
        'swap_failed_at': lambda: when(hunter.swap_failed_at),
        'step_asked_at': lambda: when(hunter.step_asked_at),
        'gather': lambda: [when(hunter.gather_looked), when(hunter.gather_waited)],
        'held': lambda: None if hunter.held is None else hunter.held.unit_id,
        'judged': lambda: [when(hunter.judged[0]), when(hunter.judged[1]), bool(hunter.judged[2])],
        'stopped_for': lambda: [
            when(hunter.stopped_for[0]),
            None if hunter.stopped_for[1] is None else hunter.stopped_for[1].unit_id,
        ],
    }
    found: dict[str, Any] = {}
    for key, part in parts.items():
        with suppress(Exception):
            found[key] = part()
    return found


def snapshot(runner: Any) -> dict[str, Any]:
    """The macro's carried state now. Never raises: a part that cannot be read is left out."""
    found: dict[str, Any] = {}
    with suppress(Exception):
        found['attack_mode'] = bool(runner.attack_mode)
        found['working'] = bool(runner.working)
        found['routine'] = runner.routine
    with suppress(Exception):
        build = runner.build
        found['build'] = build.name if build is not None else None
        found['settings'] = build.settings.model_dump(mode='json') if build is not None else None
    with suppress(Exception):
        hunter = runner.hunter
        if hunter is not None:
            found['sweep'] = int(hunter.sweep.steps)
    with suppress(Exception):
        hunter = runner.hunter
        if hunter is not None and hunter.pursuing:
            found['pursuit'] = pursuit(hunter)
    with suppress(Exception):
        hunter = runner.hunter
        if hunter is not None and hunter.pursuing and hunter.safety.decision:
            found['decision'] = hunter.safety.decision
    with suppress(Exception):
        found['route'] = route(runner.progress)
    with suppress(Exception):
        found['card'] = card(runner.target() if runner.target is not None else None)
    with suppress(Exception):
        remembered = memory(runner)
        if remembered:
            found['memory'] = remembered
    return found


def version(root: Path | None = None) -> dict[str, Any]:
    """The code a take was made by: the commit and whether the tree differed from it. Read once, at the
    service's start; {} where there is no repository to ask."""
    root = root or Path(__file__).resolve().parents[2]
    found: dict[str, Any] = {}
    with suppress(OSError, subprocess.SubprocessError):
        commit = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
        changed = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=no'],
            cwd=root, capture_output=True, text=True, timeout=5, check=True,
        ).stdout.splitlines()  # fmt: skip
        found = {'commit': commit, 'changed': sorted(line[3:] for line in changed)}
    return found
