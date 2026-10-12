"""The route catalogue as the Markdown tables of levels/routes.md.

Run: uv run --offline python -m inventory_tracking.routes            (print the tables)
     uv run --offline python -m inventory_tracking.routes --write    (put them into levels/routes.md)
"""

from collections.abc import Iterable
from pathlib import Path

from inventory_tracking.levels.exits import short_name
from inventory_tracking.routes.check import pending
from inventory_tracking.routes.model import Route


DOCUMENT = Path(__file__).parents[1] / 'levels' / 'routes.md'
BEGIN, END = '<!-- routes:begin (generated: python -m inventory_tracking.routes --write) -->', '<!-- routes:end -->'
ACTS = ((1, 39), (40, 74), (75, 102), (103, 108), (109, 132))  # the level numbers of each act


def act_of(route: Route) -> int:
    area = route.scripts[-1].area
    return next(number for number, (first, last) in enumerate(ACTS, 1) if first <= area <= last)


def row(route: Route) -> str:
    starts = ', '.join(short_name(area) for area in route.starts)
    levels = '<br>'.join(
        f'{"*" if script.alternate else ""}{short_name(script.area)}{"*" if script.alternate else ""}: '
        + ' → '.join(stage.text() for stage in script.stages)
        for script in route.scripts
    )
    return f'| {route.name} | {starts} | {levels} |'


def render(routes: Iterable[Route]) -> str:
    routes = tuple(routes)
    lines = [
        'Each row is one route: where it may start, then each level with its stages in order. A level in',
        '*italics* is passed through by this route while its own main script goes elsewhere.',
    ]
    for act in range(1, len(ACTS) + 1):
        lines += ['', f'### Act {act}', '', '| Route | Start | Levels and stages |', '| --- | --- | --- |']
        lines += [row(route) for route in routes if act_of(route) == act]
    waiting = pending(routes)
    lines += ['', f'### Pending ({len(waiting)})', '', '| Route | Level | Stage | Why |', '| --- | --- | --- | --- |']
    lines += [f'| {name} | {short_name(area)} | {stage.text()} | {stage.pending} |' for name, area, stage in waiting]
    return '\n'.join(lines)


def embedded(document: str) -> str:
    """The tables as the document holds them, between its two markers."""
    return document.split(BEGIN, 1)[1].split(END, 1)[0].strip('\n')


def embed(document: str, tables: str) -> str:
    before, rest = document.split(BEGIN, 1)
    return f'{before}{BEGIN}\n{tables}\n{END}{rest.split(END, 1)[1]}'
