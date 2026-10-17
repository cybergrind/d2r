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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
LOOP_TOOLS = HERE.parents[1] / 'd2-loop-watch' / 'tools'
sys.path.insert(0, str(LOOP_TOOLS))

import games  # ruff: ignore[module-import-not-at-top-of-file] - the loop-watch skill's log reader


ROOT = HERE.parents[3]
ASSESSMENT = 'Identify assessment: '
MATERIAL = re.compile(
    r' Rune$|^(Chipped |Flawed |Flawless |Perfect )?(Amethyst|Diamond|Emerald|Ruby|Sapphire|Topaz|Skull)$'
    r'|Worldstone Shard|Essence|^Key of|Token'
)
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


def local(text: str) -> datetime:
    return datetime.strptime(text, '%Y-%m-%d %H:%M')


def window(args) -> tuple[list[Path], list[games.Game]]:
    """The sessions that hold the last `args.games` games, and those games."""
    since = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    scope = argparse.Namespace(sessions=None, since=since)
    played = []
    for directory in games.sessions(scope):
        played += games.read(directory, since, args.until)[0]
    played = played[-args.games :]
    names = {g.session for g in played}
    return [d for d in games.sessions(scope) if d.name in names], played


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


def finds(directories: list[Path], start: datetime, until: datetime | None, places: dict) -> list[Find]:
    found: list[Find] = []
    units: set[int] = set()
    for directory in directories:
        game = None
        for line in (directory / 'probe.log').read_text(errors='replace').splitlines():
            at = games.stamp(line)
            if at is None or at < start or (until and at > until):
                continue
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
    return found


def ground(directories: list[Path], start: datetime, until: datetime | None, places: dict):
    seen = []
    for directory in directories:
        seen += games.read(directory, start, until)[3]
    taken = {(item.name, item.place) for item, _ in seen if item.picked}
    left = [(item, why) for item, why in seen if not item.picked and (item.name, item.place) not in taken]
    missed = [
        f'{i.when} game {places.get((i.session, i.game))}: {i.quality} {i.name} ({why})' for i, why in left if why
    ]
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
    return f'{f.when[11:]} game {f.game}: {f.name}{stats} - {said}{verdict}'


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--games', type=int, default=200, help='the last N games (default 200)')
    parser.add_argument('--top', type=int, default=5, help='how many finds to rank (default 5)')
    parser.add_argument('--until', type=local)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    directories, played = window(args)
    if not played:
        print(f'no games in the last {LOOKBACK_DAYS} days of logs')
        return
    start = played[0].started
    places = ordinals(played)
    found = finds(directories, start, args.until, places)
    priced = sorted((f for f in found if f.value_ist), key=lambda f: -(f.value_ist or 0))
    unpriced = [f for f in found if not f.value_ist and f.kind == 'appraised' and f.verdict not in ('vendor', '')]
    missed, design = ground(directories, start, args.until, places)
    summary = {
        'games': len(played),
        'from': str(start),
        'to': str(args.until or played[-1].started),
        'top': [asdict(f) for f in priced[: args.top]],
        'unpriced_worth_a_look': [asdict(f) for f in unpriced],
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
    print(f'\nmissed on the ground: {len(missed)}')
    for text in missed:
        print(f'  {text}')
    print(f'sets and uniques left by design: {len(design)}')
    for text in design:
        print(f'  {text}')


if __name__ == '__main__':
    main()
