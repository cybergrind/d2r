"""What one play of an arena scene gave, and the table that sets many plays side by side (framework-plan.md, Task 1.3).

Every number is on the arena's own clock: nothing here is wall time.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class Result:
    """The outcome of one play of one arena scene."""

    scene: str  # the scene's name
    seconds: float  # how long the play ran, arena clock
    dead_at: float | None  # seconds at which the character's life ran out; None: it lived
    cleared_at: float | None  # seconds at which the last hostile died; None: not cleared
    taken: float  # points of life the character lost
    kills: list[int]  # unit ids in the order they died
    casts: int  # strikes made
    moved: float  # world units the character went
    potions: list[tuple[float, int, str]] = field(default_factory=list)  # (seconds, item class id, 'serve' or 'osd')
    charges: int = 0  # Teleport charges spent
    swaps: int = 0  # weapon swaps made
    said: list[tuple[float, str]] = field(default_factory=list)  # (seconds, the macro's log line)

    @property
    def alive(self) -> bool:
        """True when the character never ran out of life."""
        return self.dead_at is None


_HEADERS = ('scene', 'alive', 'dead@', 'clear@', 'taken', 'kills', 'casts', 'moved', 'pots', 'charges', 'swaps')
_LEFT_COLUMNS = (0, 1)  # the scene name and the alive word; every other column is numeric and right-aligned


def _alive_text(alive: bool) -> str:
    """The alive column's word for a result."""
    return 'yes' if alive else 'DEAD'


def _time_text(value: float | None) -> str:
    """A time to one decimal, or '-' when it never happened."""
    return '-' if value is None else f'{value:.1f}'


def _pots_text(potions: Sequence[tuple[float, int, str]]) -> str:
    """The potion count, with the osd part shown only when some were drunk by 'osd'."""
    count = len(potions)
    osd = sum(1 for potion in potions if potion[2] == 'osd')
    return f'{count} ({osd} osd)' if osd else str(count)


def _pots_total_text(results: Sequence[Result]) -> str:
    """The potion count over many results, with the osd part as in _pots_text."""
    count = sum(len(r.potions) for r in results)
    osd = sum(1 for r in results for potion in r.potions if potion[2] == 'osd')
    return f'{count} ({osd} osd)' if osd else str(count)


def _justify(cells: Sequence[str], widths: Sequence[int]) -> str:
    """Join one line of cells, aligning each to its column width, with no trailing spaces."""
    parts = [
        cell.ljust(width) if index in _LEFT_COLUMNS else cell.rjust(width)
        for index, (cell, width) in enumerate(zip(cells, widths, strict=True))
    ]
    return '  '.join(parts).rstrip()


def scorecard(results: Sequence[Result]) -> str:
    """Return a fixed-width table: a header, a dashed rule, one row per result, then a totals row."""
    rows = [
        [
            r.scene,
            _alive_text(r.alive),
            _time_text(r.dead_at),
            _time_text(r.cleared_at),
            str(round(r.taken)),
            str(len(r.kills)),
            str(r.casts),
            str(round(r.moved)),
            _pots_text(r.potions),
            str(r.charges),
            str(r.swaps),
        ]
        for r in results
    ]
    total = [
        f'total ({len(results)})',
        f'{sum(r.alive for r in results)}/{len(results)}',
        '-',
        '-',
        str(round(sum(r.taken for r in results))),
        str(sum(len(r.kills) for r in results)),
        str(sum(r.casts for r in results)),
        str(round(sum(r.moved for r in results))),
        _pots_total_text(results),
        str(sum(r.charges for r in results)),
        str(sum(r.swaps for r in results)),
    ]
    widths = [max(len(row[column]) for row in [list(_HEADERS), *rows, total]) for column in range(len(_HEADERS))]
    lines = [_justify(list(_HEADERS), widths), _justify(['-' * width for width in widths], widths)]
    lines.extend(_justify(row, widths) for row in rows)
    lines.append(_justify(total, widths))
    return '\n'.join(lines)


def _differences(before: Result, after: Result) -> list[tuple[str, str, str]]:
    """The fields that differ, as (field, before, after) in report order, compared at the shown precision."""
    pairs = [
        ('alive', _alive_text(before.alive), _alive_text(after.alive)),
        ('taken', str(round(before.taken)), str(round(after.taken))),
        ('cleared_at', _time_text(before.cleared_at), _time_text(after.cleared_at)),
        ('kills', str(len(before.kills)), str(len(after.kills))),
        ('casts', str(before.casts), str(after.casts)),
        ('pots', str(len(before.potions)), str(len(after.potions))),
        ('charges', str(before.charges), str(after.charges)),
        ('swaps', str(before.swaps), str(after.swaps)),
    ]
    return [pair for pair in pairs if pair[1] != pair[2]]


def _verdict(before: Result, after: Result) -> str:
    """Classify one differing scene as 'WORSE', 'better' or 'changed'; WORSE is checked first."""
    taken_before, taken_after = round(before.taken), round(after.taken)
    rise = taken_after - taken_before
    fall = taken_before - taken_after
    same_state = before.alive == after.alive
    if (
        (before.alive and not after.alive)
        or (same_state and rise >= 1 and rise > 0.05 * taken_before)
        or (before.cleared_at is not None and after.cleared_at is None)
    ):
        return 'WORSE'
    if (
        (not before.alive and after.alive)
        or (same_state and fall >= 1 and fall > 0.05 * taken_before)
        or (before.cleared_at is None and after.cleared_at is not None)
    ):
        return 'better'
    return 'changed'


def compare(before: Sequence[Result], after: Sequence[Result]) -> str:
    """Report, scene by scene, what changed between two sets of plays, worst first."""
    old = {r.scene: r for r in before}
    new = {r.scene: r for r in after}
    shared = sorted(old.keys() & new.keys())
    worse: list[str] = []
    changed: list[str] = []
    better: list[str] = []
    for scene in shared:
        diffs = _differences(old[scene], new[scene])
        if not diffs:
            continue
        verdict = _verdict(old[scene], new[scene])
        text = ', '.join(f'{name} {was} -> {now}' for name, was, now in diffs)
        line = f'{verdict} {scene}: {text}'
        {'WORSE': worse, 'changed': changed, 'better': better}[verdict].append(line)
    gone = [f'gone {scene}' for scene in sorted(old.keys() - new.keys())]
    added = [f'new {scene}' for scene in sorted(new.keys() - old.keys())]
    lines = worse + changed + better + gone + added
    if not lines:
        return f'no differences ({len(shared)} scenes)'
    return '\n'.join(lines)
