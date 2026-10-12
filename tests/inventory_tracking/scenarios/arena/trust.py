"""Whether the arena may be believed for a scene cut from a recording (framework-plan.md, Task 1.9:
"a scene with `trusted` false is never used for a safety assertion").

The verdicts are fixtures/trusted.json, written by calibrate.py on the host (the recordings are not
in git): scene name -> whether the arena's monsters did to the character, and died, about as the
recording shows. A safety test over such a scene asks first:

    @needs_trust('20261011T211725Z-22-1093-burst15')
    def test_the_character_lives(): ...

    pytest.param(scene, marks=needs_trust(scene.name))

and is skipped, with the ratios as the reason, where the arena cannot be believed. A scene the file
does not name was never calibrated and is not believed either; a scene built by hand has no recording
to be held against and needs no trust.
"""

import json
from functools import cache
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / 'fixtures'
VERDICTS = 'trusted.json'
REPORT = 'CALIBRATION.md'
RATIO = 'ratio'  # the heading of both ratio columns of the report's table: the life lost first, then the kills


@cache
def verdicts(fixtures: Path = FIXTURES) -> dict[str, bool]:
    """trusted.json as it stands; nothing without the file."""
    path = fixtures / VERDICTS
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def trusted(name: str, fixtures: Path = FIXTURES) -> bool:
    """Whether the calibration believes the arena for the scene `name`; False for one it does not know."""
    return verdicts(fixtures).get(name) is True


@cache
def rows(fixtures: Path = FIXTURES) -> dict[str, dict[str, list[str]]]:
    """The scenes' rows of the report's table: scene -> column heading -> the cells under it, in order
    (two columns are headed `ratio`). Nothing without the report."""
    path = fixtures / REPORT
    if not path.exists():
        return {}
    found: dict[str, dict[str, list[str]]] = {}
    heads: list[str] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if not line.startswith('|'):
            heads = []
        elif cells[0] == 'scene':
            heads = cells
        elif heads and len(cells) == len(heads) and not set(cells[0]) <= set('-: '):
            row: dict[str, list[str]] = {}
            for head, cell in zip(heads, cells, strict=True):
                row.setdefault(head, []).append(cell)
            found[cells[0]] = row
    return found


def reason(name: str, fixtures: Path = FIXTURES) -> str:
    """Why a test over the scene is skipped: its ratios and what the calibration noted, from the report."""
    row = rows(fixtures).get(name)
    if name not in verdicts(fixtures) or row is None or len(row.get(RATIO, ())) < 2:
        return f'the arena is not calibrated for {name} (no row in {VERDICTS} and {REPORT})'
    taken, kills = row[RATIO][:2]
    notes = '; '.join(row.get('notes', ())).strip()
    return (
        f'the arena is not believed for {name}: arena / take is {taken} for the life lost and {kills} for the kills'
        + (f' ({notes})' if notes else '')
        + f' ({REPORT})'
    )


def needs_trust(name: str, fixtures: Path = FIXTURES) -> pytest.MarkDecorator:
    """The mark of a safety test over the scene `name`: a skip that says why where the arena is not
    believed for it, and a mark that does nothing where it is. One mark either way, so it serves as
    a decorator and in `pytest.param(..., marks=...)` alike."""
    believed = trusted(name, fixtures)
    return pytest.mark.skipif(not believed, reason='' if believed else reason(name, fixtures))
