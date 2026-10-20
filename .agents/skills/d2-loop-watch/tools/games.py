"""The KP_6 loop's games over a stretch of play, read from serve's probe.logs: what an improvement is measured by.

For every game (from its `next game` leg to the next game's): the seconds, each leg's seconds and how it ended (the
next game, a recovery that left it, a stop, the player's KP_6). Then:

- games, games per hour, the median and the 90th percentile of a whole game (ended games only), and the median of
  each leg;
- the slowest games with their notes (which legs took the time, what was said in them);
- every recovery, stop and error, with its clock time;
- what the loop did besides (stash visits, repairs, sales, shopping);
- TZ leveling's experience (lines since 2026-10-19 21:37): a game's gain, experience an hour over the games' whole
  time, the loop's own rate since it turned on (its last line), and the levels by experience a minute;
- the ground: every item the census saw (`Macro: ground:`) matched against the pickups of its game, and those never
  picked up sorted: MISSED is what the sure mode takes (pickmode.py `sure`: runes but the full stash stacks, the gems
  and charms and jewels the read lists, rare / set / unique rings and amulets, uniques and sets the loot filter shows
  or the marks price, what the marks point at); the rest is left by design, its sets, uniques and rares counted for a
  look (the appraise skill gives a verdict, not this).

The census's own word is not the pickup's: "left" is said when an item is first seen, before it lands, and "taken
(material)" only says the read listed it (2026-10-17: magic rings said "taken" and never picked in the sure mode).

    python3 .agents/skills/d2-loop-watch/tools/games.py [--since 'YYYY-MM-DD HH:MM'] [--until ...] [--last N]
                                                       [--sessions DIR...] [--slowest 8] [--json]

Default: the sessions of the last 24 hours. Times are the logs' (local).
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import logwords
from logwords import (
    AIMED,
    DID,
    EVENT,
    EXPERIENCE_GAME,
    EXPERIENCE_LEVEL,
    FULL,
    GAME_LEFT,
    GROUND,
    LEG,
    LOOP_OFF,
    LOOP_ON,
    LOOP_STOPPED,
    PICKED,
    REQUEST_LOOP,
    STOPS_HERE,
    amount,
    stamp,
)


ROOT = Path(__file__).resolve().parents[4]
RUNS = ROOT / 'inventory_tracking' / 'runs' / 'alt-d'
GEM = re.compile(r'^(Chipped |Flawed |Flawless |Perfect )?(Amethyst|Diamond|Emerald|Ruby|Sapphire|Topaz|Skull)$')
MARKED = re.compile(r'Essence|Key of|Token|Worldstone Shard|Statue')
JEWELRY_QUALITIES = ('rare', 'set', 'unique')


@dataclass
class Seen:
    """An item the ground census saw in a game, and whether a pickup of the game took it."""

    when: str
    session: str
    game: int | None
    quality: str
    name: str
    label: str
    place: tuple[int, int]
    verdicts: set[str] = field(default_factory=set)  # the census's words after 'taken (...)'; empty: only "left"
    picked: bool = False
    last: int = 0  # the log line the census last said it on

    def missed(self, full: set[str]) -> str | None:
        """Why the sure mode would have taken it (pickmode.py `sure`), None for an item left by design."""
        name, said = self.name, self.verdicts
        if name in full:
            return None  # a full stash stack's kind (runes, gems): not picked up by design (macros/loop.py `full`)
        if said & {'unique', 'named'}:
            return 'a unique or set item the filter shows or the marks price'
        if name.endswith(' Rune'):
            return 'a rune'
        if GEM.match(name) or 'Charm' in name or name in ('Jewel', 'Colossal Jewel'):
            return 'a gem, charm or jewel the read listed' if said else None  # only "left": the filter hides it
        if name in ('Ring', 'Amulet') and self.quality in JEWELRY_QUALITIES:
            return f'a {self.quality} {name.lower()}'
        if said and MARKED.search(name):
            return 'what the marks point at'
        return None


def full_stacks() -> set[str]:
    """The names of the stash's full stacks (runs/alt-d/full-stacks.json, by the repo's item metadata)."""
    try:
        sys.path.insert(0, str(ROOT))
        from inventory_tracking.items.metadata import item_base

        ids = json.loads((RUNS / 'full-stacks.json').read_text())
        return {base['name'] for base in map(item_base, ids) if base}
    except ImportError, OSError, ValueError:
        return set()


def reconcile(seen: list[Seen], picks: list[str], aims: dict[str, set[tuple[int, int]]]) -> None:
    """Mark the census's items of one game that a pickup took: by the place a pickup of that name aimed at first,
    then by the name alone (a pile's later items are taken in the same press, not named with a place)."""

    def names(item: Seen) -> set[str]:
        return {item.name, item.label, f'{item.quality.capitalize()} {item.name}'}

    left = list(picks)
    for label in list(left):
        places = aims.get(label, set())
        for item in seen:
            near = any(abs(item.place[0] - x) <= 2 and abs(item.place[1] - y) <= 2 for x, y in places)
            if not item.picked and near and label in names(item):
                item.picked = True
                left.remove(label)
                break
    for label in left:
        for item in seen:
            if not item.picked and label in names(item):
                item.picked = True
                break


@dataclass
class Game:
    number: int
    session: str
    started: datetime
    legs: dict[str, float] = field(default_factory=dict)
    ended: datetime | None = None
    end: str = 'open'  # 'next', 'left' (a recovery), 'stopped', 'player'
    notes: list[str] = field(default_factory=list)
    # A terror zone game's experience line (EXPERIENCE_GAME): its gain and the loop's rate since it turned on ('?')
    experience: int | None = None
    rate: str | None = None
    levels: list[tuple[str, int, int]] = field(default_factory=list)  # (level, gain, seconds) as each was left

    @property
    def seconds(self) -> float | None:
        return (self.ended - self.started).total_seconds() if self.ended else None


def sessions(args) -> list[Path]:
    if args.sessions:
        return [Path(s) for s in args.sessions]
    return logwords.sessions(args.since or datetime.now() - timedelta(hours=24), runs=RUNS)


def clicked(items: Iterable[Seen], clicks: list[tuple[tuple[int, int], int]]) -> None:
    """Mark taken each item a pickup's click landed on (within 2 units) that the census never said again after it."""
    for item in items:
        if any(abs(item.place[0] - x) <= 2 and abs(item.place[1] - y) <= 2 and item.last < n for (x, y), n in clicks):
            item.picked = True


def read(directory: Path, since: datetime | None, until: datetime | None):
    games: list[Game] = []
    events: list[str] = []
    did: Counter[str] = Counter()
    ground: list[Seen] = []
    full: set[str] = set()
    # One game's census (the census says an item 2-4 times: once per name and place), pickups and their aims
    items: dict[tuple, Seen] = {}
    picks: list[str] = []
    aims: dict[str, set[tuple[int, int]]] = {}
    # A pickup's click on an item, its press cut before "picked up" was said (15:02:56 and 15:22:10 on 2026-10-18:
    # "aims for Jewel ... clicked", then "priced act expired"; 15:34:06, the click from 9 away took it and the aims
    # found nothing): taken when the census never says it again (each confirmed by Cain's appraisal after)
    clicks: list[tuple[tuple[int, int], int]] = []
    game: Game | None = None
    leg: tuple[str, datetime] | None = None
    asked = False

    def settle() -> None:
        clicked(items.values(), clicks)
        clicks.clear()
        reconcile(list(items.values()), picks, aims)
        ground.extend(items.values())
        items.clear()
        picks.clear()
        aims.clear()

    def close(at: datetime, how: str) -> None:
        nonlocal game, leg
        if game is not None:
            if leg is not None:
                game.legs[leg[0]] = game.legs.get(leg[0], 0) + (at - leg[1]).total_seconds()
            game.ended, game.end = at, how
        game, leg = None, None

    for number_of_line, line in enumerate((directory / 'probe.log').read_text(errors='replace').splitlines()):
        at = stamp(line)
        if at is None or (since and at < since) or (until and at > until):
            continue
        if REQUEST_LOOP in line:
            asked = True
        if (m := FULL.search(line)) is not None:
            full.add(m.group(1))
        if (m := LEG.search(line)) is not None:
            number, name = int(m.group(1)), m.group(2).strip()
            if game is None or game.number != number:
                if game is not None:  # what was seen before a session's first leg is its first game's (a restart)
                    settle()
                close(at, 'next')
                game = Game(number, directory.name, at)
                games.append(game)
            elif leg is not None:
                game.legs[leg[0]] = game.legs.get(leg[0], 0) + (at - leg[1]).total_seconds()
            leg = (name, at)
            continue
        if LOOP_OFF in line:
            close(at, 'player' if asked else 'stopped')
            asked = False
            continue
        if LOOP_ON in line:
            asked = False
        if (m := EVENT.search(line)) is not None:
            text = f'{line[:19]} {m.group(0)[:200]}'
            events.append(text)
            if game is not None:
                game.notes.append(m.group(0)[:100])
            if GAME_LEFT in line:
                close(at, 'left')
            elif LOOP_STOPPED in line or STOPS_HERE in line:
                close(at, 'stopped')
            continue
        if (m := EXPERIENCE_GAME.search(line)) is not None:
            if game is not None and game.number == int(m.group(1)):
                game.experience, game.rate = amount(m.group(2)), m.group(5)
            continue
        if (m := EXPERIENCE_LEVEL.search(line)) is not None:
            if game is not None:
                game.levels.append((m.group(1), amount(m.group(2)), int(m.group(3))))
            continue
        if (m := DID.search(line)) is not None:
            kind = m.group(1).split(':')[0]
            did[kind] += 1
            if game is not None and kind in ('repair', 'shop'):
                game.notes.append(m.group(1)[:100])
            continue
        if (m := PICKED.search(line)) is not None:
            picks.append(m.group(1))
            continue
        if (m := AIMED.search(line)) is not None:
            label = m.group(1) or m.group(4)
            x, y = (m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(6))
            aims.setdefault(label, set()).add((round(float(x)), round(float(y))))
            if m.group(4):  # an aim after the press's click (15:34:06: the click from 9 away walked and took it)
                clicks.append(((round(float(x)), round(float(y))), number_of_line))
            continue
        if (m := GROUND.search(line)) is not None:
            quality, name, label = m.group(1), m.group(2), m.group(5) or ''
            place = (int(m.group(6)), int(m.group(7)))
            item = items.get((quality, name, place))
            if item is None:
                item = items[quality, name, place] = Seen(
                    line[11:19], directory.name, game.number if game else None, quality, name, label, place
                )
            elif item.game is None and game is not None:
                item.game = game.number
            item.last = number_of_line
            if m.group(8):
                item.verdicts.add(m.group(8))
    settle()
    full |= full_stacks()
    for item in ground:
        if item.game is None and game is not None:
            item.game = game.number
    return games, events, did, [(item, item.missed(full)) for item in ground]


def quantile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def experience(games: list[Game]) -> dict | None:
    """The terror zone games' experience: per game, an hour over the ended games' whole time, the loop's last rate, the
    levels by experience a minute; None without an experience line."""
    told = [g for g in games if g.experience is not None]
    if not told:
        return None
    timed = [g for g in told if g.end == 'next' and g.seconds]
    seconds = sum(g.seconds or 0 for g in timed)
    levels: dict[str, list[int]] = {}
    for g in told:
        for name, gain, spent in g.levels:
            level = levels.setdefault(name, [0, 0, 0])
            level[0], level[1], level[2] = level[0] + gain, level[1] + spent, level[2] + 1
    return {
        'games': len(told),
        'median_a_game': statistics.median(g.experience for g in told if g.experience is not None),
        'an_hour': round(3600 * sum(g.experience or 0 for g in timed) / seconds) if seconds else None,
        'loop_rate': told[-1].rate,
        'levels_a_minute': {
            name: {'a_minute': round(60 * gain / spent) if spent else None, 'gain': gain, 'visits': visits}
            for name, (gain, spent, visits) in sorted(levels.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1))
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--since', type=lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M'))
    parser.add_argument('--until', type=lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M'))
    parser.add_argument('--last', type=int, help='only the last N games')
    parser.add_argument('--sessions', nargs='*')
    parser.add_argument('--slowest', type=int, default=8)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    games: list[Game] = []
    events: list[str] = []
    did: Counter[str] = Counter()
    ground: list[tuple[Seen, str | None]] = []
    for directory in sessions(args):
        g, e, d, u = read(directory, args.since, args.until)
        games += g
        events += e
        did += d
        ground += u
    # A game a restart cut goes on in the next session's log: an item it picked up there, at the same place, is taken
    taken = {(item.name, item.place) for item, _ in ground if item.picked}
    unpicked = [(item, why) for item, why in ground if not item.picked and (item.name, item.place) not in taken]
    missed = [(item, why) for item, why in unpicked if why]
    look = Counter(
        f'{item.quality} {item.name}' if item.quality in ('set', 'unique') else f'{item.quality} (any)'
        for item, why in unpicked
        if not why and item.quality in ('set', 'unique', 'rare')
    )
    if args.last:
        games = games[-args.last :]
    ended = [g for g in games if g.end == 'next' and g.seconds is not None]
    times = [g.seconds for g in ended if g.seconds is not None]
    legs: dict[str, list[float]] = {}
    for g in ended:
        for name, seconds in g.legs.items():
            legs.setdefault(name, []).append(seconds)
    span = (games[-1].started - games[0].started).total_seconds() / 3600 if len(games) > 1 else 0
    summary = {
        'games': len(games),
        'ended_by': dict(Counter(g.end for g in games)),
        'per_hour': round(len(games) / span, 1) if span else None,
        'median_s': round(statistics.median(times), 1) if times else None,
        'p90_s': round(quantile(times, 0.9), 1) if times else None,
        'legs_median_s': {n: round(statistics.median(v), 1) for n, v in legs.items()},
        'did': dict(did),
        'events': events,
        'missed': [
            {
                'when': i.when,
                'session': i.session,
                'game': i.game,
                'item': f'{i.quality} {i.name}',
                'at': i.place,
                'why': why,
            }
            for i, why in missed
        ],
        'left_by_design_worth_a_look': dict(look.most_common()),
        'experience': experience(games),
    }
    if args.json:
        print(json.dumps(summary, indent=1, default=str))
        return
    first, last = (games[0].started, games[-1].started) if games else (None, None)
    print(f'{len(games)} games {first} .. {last}; ended by {summary["ended_by"]}; {summary["per_hour"]}/h')
    print(f'whole game (ended to the next): median {summary["median_s"]} s, p90 {summary["p90_s"]} s')
    print('legs (median s): ' + ', '.join(f'{n} {s}' for n, s in summary['legs_median_s'].items()))
    print(f'did: {dict(did)}')
    if (exp := summary['experience']) is not None:
        print(f'experience (TZ, {exp["games"]} games): median {exp["median_a_game"]:+,.0f} a game, '
              f'{exp["an_hour"] if exp["an_hour"] is None else format(exp["an_hour"], ",")} an hour over the ended '
              f'games\' time; the loop said {exp["loop_rate"]} an hour since it turned on')  # fmt: skip
        print('  levels (experience a minute, gain, visits): ' + ', '.join(
            f'{name} {row["a_minute"]:,}/min {row["gain"]:+,} x{row["visits"]}'
            for name, row in list(exp['levels_a_minute'].items())[:8] if row['a_minute'] is not None
        ))  # fmt: skip
    print(f'\nslowest {args.slowest}:')
    for g in sorted(ended, key=lambda g: -(g.seconds or 0))[: args.slowest]:
        top = ', '.join(f'{n} {s:.0f}s' for n, s in sorted(g.legs.items(), key=lambda kv: -kv[1])[:3])
        print(f'  {g.started:%H:%M:%S} game {g.number} ({g.session[:16]}): {g.seconds:.0f}s: {top}'
              f'{"; " + "; ".join(g.notes[:3]) if g.notes else ""}')  # fmt: skip
    print(f'\nrecoveries, stops, errors ({len(events)}):')
    for text in events[-30:]:
        print(f'  {text}')
    print(f'\nMISSED: never picked up, though the sure mode takes it ({len(missed)}):')
    for item, why in missed:
        print(
            f'  {item.when} game {item.game} ({item.session[-8:]}): {item.quality} {item.name} at {item.place}: {why}'
        )
    print(f'\nleft by design (the filter or the sure mode), worth a look ({sum(look.values())}):')
    for name, count in look.most_common(25):
        print(f'  {count:4} {name}')


if __name__ == '__main__':
    main()
