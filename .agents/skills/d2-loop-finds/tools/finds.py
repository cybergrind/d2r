"""The KP_6 loop's most valuable finds over its last games, read from serve's probe.logs and priced offline.

The player, 2026-10-17: "check logs and bring 5 most expensive findings in the last 200 games".

- **window**: the last `--games` games (`games.py`: a game runs from its `next game` leg to the next game's), to the
  end of the logs or `--until`;
- **appraised**: every item Cain identified (`Identify assessment: {...}`, appraisal/service.py), with the triage's
  verdict, its band (lower quartile and median asks, sellers, date) and its stats;
- **materials**: runes, gems, shards, essences, keys and tokens picked up (`Macro: picked up <name>`), each priced by
  `pricing.knowledge lookup` (offline): the ladder's Ist value when it has one, else the market's median ask;
- **ranked** by the value a trade can count on: the triage's `decision_ist` (the band's lower quartile) for an
  appraised item, the ladder value or median ask for a material. Appraised items with no price whose verdict is not
  `vendor` are listed apart ("unpriced, worth a look"): the knowledge base cannot rank them;
- **the ground**: what the sure mode would have taken and the window left (`games.py` MISSED), and the sets and uniques
  left by design.

    python3 .agents/skills/d2-loop-finds/tools/finds.py [--games 200] [--top 5] [--until 'YYYY-MM-DD HH:MM'] [--json]
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
LOOP_TOOLS = HERE.parents[1] / 'd2-loop-watch' / 'tools'
sys.path.insert(0, str(LOOP_TOOLS))

import games  # ruff: ignore[module-import-not-at-top-of-file] - the loop-watch skill's log reader
import logwords  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool


ROOT = HERE.parents[3]
ASSESSMENT = 'Identify assessment: '
MATERIAL = re.compile(
    r' Rune$|^(Chipped |Flawed |Flawless |Perfect )?(Amethyst|Diamond|Emerald|Ruby|Sapphire|Topaz|Skull)$'
    r'|Worldstone Shard|Essence|^Key of|Token'
    r"|^(Talic's Anguish|Korlic's Pain|Madawc's Ire|Bul-Kathos' Nightmare|Worusk's End)$"
)
# The Uber Ancients' statues (loot/materials.py STATUE_NAMES; picked as materials, config `material_marks`): priced as a
# material when the knowledge base can, else listed as unpriced. The player, 2026-10-25: "it looks like we don't factor
# statues, do we?"
STATUE = re.compile(r"^(Talic's Anguish|Korlic's Pain|Madawc's Ire|Bul-Kathos' Nightmare|Worusk's End)$")
LOOKBACK_DAYS = 7  # how far back the sessions are searched for the window's games


@dataclass
class Find:
    when: str
    session: str
    game: int | None  # the game's place in the window, 1 the oldest (the loop's own count starts anew at a restart)
    name: str
    kind: str  # 'appraised' or 'material'
    value_ist: float | None  # what the ranking counts
    median_ist: float | None = None
    verdict: str = ''
    reason: str = ''
    stats: list[str] = field(default_factory=list)
    evidence: str = ''


def window(args) -> tuple[list[Path], list[games.Game], dict[str, list]]:
    """The sessions that hold the last `args.games` games, those games, and each session's ground (`games.read`).

    Read newest first, stopping once the window is full: a week holds hundreds of sessions where 200 games take
    30 to 60 (2026-10-23: reading the whole week first took 74 of the tool's 111 s)."""
    since = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    scope = argparse.Namespace(sessions=None, since=since)
    held: list[tuple[Path, list[games.Game]]] = []
    seen: dict[str, list] = {}
    count = 0
    for directory in reversed(games.sessions(scope)):
        found = games.read(directory, since, args.until)
        if not found[0]:
            continue
        held.append((directory, found[0]))
        seen[directory.name] = found[3]
        count += len(found[0])
        if count >= args.games:
            break
    held.reverse()
    played = [g for _, session in held for g in session][-args.games :]
    names = {g.session for g in played}
    return [d for d, _ in held if d.name in names], played, seen


def appraised(item: dict, at: str, session: str, game: int | None) -> Find:
    triage = item.get('triage') or {}
    band = triage.get('band') or {}
    reference = triage.get('reference_band') or {}
    evidence = ''
    if band or reference:
        shown = band or reference
        evidence = (
            f'{"" if band else "reference only: "}asks q1 {shown.get("q1_ist")} / median {shown.get("median_ist")} '
            f'Ist, {shown.get("sellers")} sellers, {shown.get("observed_at")}'
        )
    return Find(
        at,
        session,
        game,
        item.get('name', '?'),
        'appraised',
        triage.get('decision_ist'),
        band.get('median_ist'),
        triage.get('verdict', item.get('verdict', '')),
        triage.get('reason', item.get('reason', '')),
        item.get('stats', []),
        evidence,
    )


def price(name: str) -> tuple[float | None, float | None, str]:
    """(value, median ask, evidence) of a material by the offline knowledge base."""
    done = subprocess.run(
        ['uv', 'run', '--offline', 'python', '-m', 'pricing.knowledge', 'lookup', name, '--limit', '1'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        found = json.loads(done.stdout)
    except ValueError:
        return None, None, 'lookup failed'
    market = found.get('market') or {}
    median = market.get('median_ist')
    for row in (found.get('evidence') or {}).get('currency', []):
        details = row.get('details') or {}
        if details.get('ist') is not None:
            return details['ist'], median, f'ladder {details["ist"]} Ist ({details.get("date")}), asks median {median}'
    if median is not None:
        return median, median, f'asks median {median} Ist, {market.get("priced_sellers")} sellers'
    return None, None, 'no price in the knowledge base'


def ordinals(played: list[games.Game]) -> dict[tuple[str, int], int]:
    """(session, the loop's game number) -> the game's place in the window, 1 the oldest."""
    return {(g.session, g.number): place for place, g in enumerate(played, 1)}


def finds(
    directories: list[Path], start: datetime, until: datetime | None, places: dict
) -> tuple[list[Find], dict[str, list[tuple[int, str]]]]:
    """The window's finds, and each session's loop stops (`logwords.STOPPED`) by their log line, for `ground`."""
    found: list[Find] = []
    stops: dict[str, list[tuple[int, str]]] = {}
    units: set[int] = set()
    for directory in directories:
        game = None
        for number, line in enumerate((directory / 'probe.log').read_text(errors='replace').splitlines()):
            at = games.stamp(line)
            if at is None or at < start or (until and at > until):
                continue
            if (m := logwords.STOPPED.search(line)) is not None:
                stops.setdefault(directory.name, []).append((number, m.group(1)))
            if (m := games.LEG.search(line)) is not None:
                game = places.get((directory.name, int(m.group(1))))
            elif (m := games.PICKED.search(line)) is not None and MATERIAL.search(m.group(1)):
                found.append(Find(line[:19], directory.name, game, m.group(1), 'material', None))
            elif ASSESSMENT in line:
                try:
                    items = ast.literal_eval(line.split(ASSESSMENT, 1)[1]).get('items', [])
                except ValueError, SyntaxError:
                    continue
                for item in items:
                    if item.get('unit_id') in units:
                        continue
                    units.add(item.get('unit_id'))
                    found.append(appraised(item, line[:19], directory.name, game))
    prices = {name: price(name) for name in {f.name for f in found if f.kind == 'material'}}
    for f in found:
        if f.kind == 'material':
            f.value_ist, f.median_ist, f.evidence = prices[f.name]
    return found, stops


# A loop stop this many log lines after a missed item's last sighting is told with it (the trips back to an item
# that cannot be reached take ~30 lines: game 55 on 2026-10-21, a Large Charm "no way over the rooms")
STOP_LINES = 300


def ground(
    directories: list[Path],
    start: datetime,
    until: datetime | None,
    places: dict,
    read: dict[str, list],
    stops: dict[str, list[tuple[int, str]]],
):
    """`read`: each session's ground from `window`; only the oldest session, which the window's start may cut, is read
    again from `start`. A missed item is told with what explains it: no loop game (a restart's or the player's own
    play: 2026-10-21 08:28-08:43, the player's Gheed's Fortune and Vipermagi "taken" in town were called missed) and
    the loop stop that named it."""
    seen = []
    for number, directory in enumerate(directories):
        seen += games.read(directory, start, until)[3] if number == 0 else read[directory.name]
    taken = {(item.name, item.place) for item, _ in seen if item.picked}
    left = [(item, why) for item, why in seen if not item.picked and (item.name, item.place) not in taken]
    missed = []
    for i, why in left:
        if not why:
            continue
        place = places.get((i.session, i.game))
        notes = [why]
        if place is None:
            notes.append('outside a loop game of the window: a restart or the player')
        stop = next(
            (text for n, text in stops.get(i.session, []) if i.first <= n <= i.last + STOP_LINES and i.name in text),
            None,
        )
        if stop is not None:
            notes.append(f'LOOP DEFECT, the loop stopped: {stop[:140]}')
        missed.append(f'{i.when} game {place}: {i.quality} {i.name} ({"; ".join(notes)})')
    design = [
        f'{i.when} game {places.get((i.session, i.game))}: {i.quality} {i.name}'
        for i, why in left
        if not why and i.quality in ('set', 'unique')
    ]
    return missed, design


def line(f: Find) -> str:
    stats = f' [{", ".join(f.stats)}]' if f.stats else ''
    verdict = f'; {f.verdict}' if f.verdict else ''
    said = '; '.join(text for text in (f.evidence, f.reason if f.kind == 'appraised' else '') if text)
    return f'{f.when[5:]} game {f.game}: {f.name}{stats} - {said}{verdict}'


def rest(found: list[Find]) -> tuple[dict[str, int], dict[str, int]]:
    """The window's materials by name and its appraised items by verdict: the report's one line on the small finds."""
    materials = Counter(f.name for f in found if f.kind == 'material')
    verdicts = Counter(f.verdict or 'none' for f in found if f.kind == 'appraised')
    return dict(materials.most_common()), dict(verdicts.most_common())


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--games', type=int, default=200, help='the last N games (default 200)')
    parser.add_argument('--top', type=int, default=5, help='how many finds to rank (default 5)')
    parser.add_argument('--until', type=logwords.local)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    directories, played, read = window(args)
    if not played:
        print(f'no games in the last {LOOKBACK_DAYS} days of logs')
        return
    start = played[0].started
    places = ordinals(played)
    found, stops = finds(directories, start, args.until, places)
    priced = sorted((f for f in found if f.value_ist), key=lambda f: -(f.value_ist or 0))
    unpriced = [
        f
        for f in found
        if not f.value_ist and (STATUE.search(f.name) if f.kind == 'material' else f.verdict not in ('vendor', ''))
    ]
    missed, design = ground(directories, start, args.until, places, read, stops)
    materials, verdicts = rest(found)
    summary = {
        'games': len(played),
        'from': str(start),
        'to': str(args.until or played[-1].started),
        'top': [asdict(f) for f in priced[: args.top]],
        'unpriced_worth_a_look': [asdict(f) for f in unpriced],
        'materials': materials,
        'appraised_verdicts': verdicts,
        'missed_on_the_ground': missed,
        'sets_and_uniques_left_by_design': design,
    }
    if args.json:
        print(json.dumps(summary, indent=1, default=str))
        return
    print(f'{len(played)} games {summary["from"][:19]} .. {summary["to"][:19]}; {len(found)} finds priced or appraised')
    print(f'games are numbered by their place in the window: 1 the oldest, {len(played)} the newest')
    print(f'\ntop {args.top} by value (Ist; appraised: lower quartile of asks; materials: ladder or median ask):')
    for number, f in enumerate(priced[: args.top], 1):
        print(f'  {number}. {f.value_ist:.2f}  {line(f)}')
    print('\nunpriced, worth a look:' if unpriced else '\nunpriced, worth a look: none')
    for f in unpriced:
        print(f'  {line(f)}')
    print('\nthe rest: ' + ', '.join(f'{count} {name}' for name, count in materials.items()))
    print(f'appraised: {sum(verdicts.values())} (' + ', '.join(f'{k} {v}' for k, v in verdicts.items()) + ')')
    print(f'\nmissed on the ground: {len(missed)}')
    for text in missed:
        print(f'  {text}')
    # The list is long (100-200) and the report counts it: --json has every one
    print(f'sets and uniques left by design: {len(design)} (--json lists them)')


if __name__ == '__main__':
    main()
