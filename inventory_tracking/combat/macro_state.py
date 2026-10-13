"""What the macro holds between its looks at the game, as a plain row for the combat recorder.

A take's frames say what stood where; what the macro did with them also hangs on what it carried:
whether attack mode is wanted, which routine works, the build chosen, how far the route is in this
game and the mark the level card leads with. `snapshot` reads those off a `MacroRunner` without
touching it (attribute reads from the recorder's thread; a value caught mid-change is of the frame
before or the frame after, and the next snapshot rights it). The recorder writes the row as a `state`
event when a take opens and whenever it differs from the one written last (combat/record.py), so an
incident can be replayed "as it was" without anything taken from the log by hand.
"""

import subprocess
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
        found['route'] = route(runner.progress)
    with suppress(Exception):
        found['card'] = card(runner.target() if runner.target is not None else None)
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
