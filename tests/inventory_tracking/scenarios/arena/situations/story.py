"""One play told in a few lines: what the character did and how it ended (user, 2026-10-13: "what we will
do and how we will die").

`story(outcome)` picks the moments of an `Outcome` (situation.py) that change the picture and says each in
one line with its time: the start (the life, attack mode, the hostiles and how many of them are near), what
the macro said first of each kind of thing (a strike, a walk, a hop, a potion, a pickup, a pause), packs that
appeared, the life at each quarter it crossed, and the end: the death with the blows of its last 1.5 s by
type, or the survival with what was left. Nothing in it is computed here that the outcome does not hold.
"""

from collections.abc import Sequence

from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome


# The macro's lines worth a place in a story, by what they begin with -> the story's words (None: the line itself).
TOLD = (
    ('Attack mode on', None),
    ('Attack mode off', None),
    ('Attack mode paused', 'attack mode pauses for a step'),
    ('Echoing Strike', 'first strike'),
    ('Psychic Ward', 'casts Psychic Ward'),
    ('Teleport toward', None),
    ('Blade Warp toward', None),
    ('Walking toward', None),
    ('Stepping to a better place', None),
    ('Rejuvenation potion', 'the macro drinks a rejuvenation'),
    ('Healing potion', 'the macro drinks a healing potion'),
    ('Picking up', None),
    ('Nothing left in reach', None),
    ('Opening', None),
)
MOST_LINES = 18


def near(outcome: Outcome, at: float) -> int:
    return next((count for when, count in reversed(outcome.crowd) if when <= at + 1e-9), 0)


def life_at(outcome: Outcome, at: float) -> float:
    return next(
        (life for when, life in reversed(outcome.life) if when <= at + 1e-9),
        outcome.life[0][1] if outcome.life else 0.0,
    )


def moments(outcome: Outcome) -> list[tuple[float, str]]:
    found: list[tuple[float, str]] = []
    seen: set[str] = set()
    for at, text in outcome.said:
        text = text.removeprefix('Macro: ').removeprefix('Macro ')
        for start, words in TOLD:
            if text.startswith(start) and start not in seen:
                seen.add(start)
                found.append((at, words or text))
    for at, label, count in outcome.appeared:
        found.append((at, f'{label} appear' if label else f'{count} monsters appear'))
    for at, label in outcome.picked:
        found.append((at, f'picks up {label}'))
    for at, _, who in outcome.potions:
        if who == 'osd':
            found.append((at, 'the healer drinks'))
    quarter = 4
    for at, life in outcome.life:
        share = int(life / outcome.max_life * 4)
        if share < quarter:
            quarter = share
            found.append(
                (at, f'life {life:.0f} of {outcome.max_life:.0f}, {near(outcome, at)} hostiles within 12 units')
            )
    for name, when in outcome.boss_dead.items():
        if when is not None:
            found.append((when, f'{name} dies'))
    return sorted(found)


def thinned(lines: Sequence[tuple[float, str]], most: int) -> list[tuple[float, str]]:
    """At most `most` lines: every repeat of "the healer drinks" after the first goes first."""
    kept, healer = [], 0
    for line in lines:
        if line[1] == 'the healer drinks':
            healer += 1
            if healer > 1:
                continue
        kept.append(line)
    return kept[:most]


def ending(outcome: Outcome) -> str:
    kills = f'{len(outcome.kills)} of {outcome.hostiles} hostiles killed'
    spent = f'{len(outcome.potions)} potions, {len(outcome.strikes)} strikes, moved {outcome.moved:.0f} units'
    if outcome.dead_at is not None:
        blows = ', '.join(
            f'{count} {name} {kind}{"s" if count > 1 else ""} ({points:.0f})'
            for name, kind, count, points in outcome.killers
        )
        return f'{outcome.dead_at:5.1f} s  DIES: {blows or "no blow in the last 1.5 s"}. {kills}; {spent}.'
    cleared = (
        f'cleared at {outcome.cleared_at:.1f} s' if outcome.cleared_at is not None else f'{outcome.alive} hostiles left'
    )
    return (
        f'{outcome.seconds:5.1f} s  alive with {life_at(outcome, outcome.seconds):.0f} of {outcome.max_life:.0f} '
        f'(least {outcome.low:.0f}), {cleared}. {kills}; {spent}; lost {outcome.taken:.0f}.'
    )


def story(outcome: Outcome) -> str:
    start = outcome.start_life
    mode = 'on' if any(text.endswith('Attack mode on') and at < 0.1 for at, text in outcome.said) else 'off'
    lines = [
        f'{outcome.name}, seed {outcome.seed}: life {start:.0f} of {outcome.max_life:.0f} '
        f'({start / outcome.max_life:.0%}), attack mode {mode}, {outcome.hostiles} hostiles, '
        f'{near(outcome, 0.0)} within 12 units.'
    ]
    until = outcome.dead_at if outcome.dead_at is not None else outcome.seconds
    lines += [f'{at:5.1f} s  {text}' for at, text in thinned(moments(outcome), MOST_LINES) if at <= until + 1e-9]
    lines.append(ending(outcome))
    taken = list(outcome.taken_by().items())[:4]
    if taken:
        lines.append(
            '        life taken by: ' + ', '.join(f'{name} {kind} {points:.0f}' for (name, kind), points in taken)
        )
    return '\n'.join(lines)
