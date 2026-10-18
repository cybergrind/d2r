"""Terror Zone farming, measured per stay in a level (the player, 2026-10-17: "monitor process of farming TZ, we need to
improve routing and full map clear speed").

The measure is **kills a minute of time in the zone's levels**: a full clear is worth its kills. Per stay (one combat
take, `inventory_tracking/runs/combat/<UTC>-<area>`): the level, seconds, kills (`kill` events), hostiles seen, the
share of them killed, the time casting / moving / standing (the character's modes, combat/legs.py CASTING and MOVING),
the longest stretch standing, Teleports, and the Herald if one came (stat 367 with the unique flag 0x08,
terror/tracker.py). Towns and stays under MIN_SECONDS are left out.

    uv run --offline python .agents/skills/d2-loop-watch/tools/tz.py [--since 'YYYY-MM-DD HH:MM'] [--until ...]
        [--against SINCE UNTIL]

`--against` prints the same totals for an earlier window and the shift of kills a minute.
"""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from logwords import TELEPORT  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool

from inventory_tracking.combat.legs import CASTING, MOVING  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.combat.takes import Take  # ruff: ignore[module-import-not-at-top-of-file]


COMBAT = ROOT / 'inventory_tracking' / 'runs' / 'combat'
TOWNS = {1, 40, 75, 103, 109}
MIN_SECONDS = 10.0
HERALD_TIER, UNIQUE = '367', 0x08


def local(text: str) -> datetime:
    return datetime.strptime(text, '%Y-%m-%d %H:%M').astimezone()


def level_names() -> dict[int, str]:
    rows = json.loads((ROOT / 'third-parties' / 'd2data' / 'json' / 'levels.json').read_text())
    rows = rows.values() if isinstance(rows, dict) else rows
    return {int(row['Id']): row.get('LevelName') or '' for row in rows if row.get('Id') is not None}


def takes_in(since: datetime, until: datetime) -> list[Path]:
    low = since.astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    high = until.astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    found = []
    for path in COMBAT.glob('*Z-*'):
        stamp, _, area = path.name.partition('Z-')
        if low <= stamp <= high and area.isdigit() and int(area) not in TOWNS:
            found.append(path)
    return sorted(found)


def stay(path: Path) -> dict | None:
    take = Take.load(path)
    if take.seconds < MIN_SECONDS:
        return None
    casting = moving = standing = longest = run = 0.0
    for before, after in zip(take.frames, take.frames[1:], strict=False):
        step = after['t'] - before['t']
        mode = before['p'][1] if before.get('p') else None
        if mode in CASTING:
            casting += step
            run = 0.0
        elif mode in MOVING:
            moving += step
            run = 0.0
        else:
            standing += step
            run += step
            longest = max(longest, run)
    hostile = {u['unit'] for u in take.units if not u.get('ally') and u.get('owner') in (None, 4294967295)}
    kills = sum(e['event'] == 'kill' for e in take.events)
    heralds = [
        u
        for u in take.units
        if HERALD_TIER in (u.get('stats') or {}) and u.get('flags', 0) & UNIQUE and not u.get('ally')
    ]
    teleports = sum(e['event'] == 'log' and TELEPORT in e.get('text', '') for e in take.events)
    return {
        'take': path.name,
        'area': int(take.manifest.get('area', 0)),
        'seconds': take.seconds,
        'kills': kills,
        'seen': len(hostile),
        'casting': casting,
        'moving': moving,
        'standing': standing,
        'longest': longest,
        'teleports': teleports,
        'herald': heralds[0]['stats'][HERALD_TIER] if heralds else None,
    }


def rows_in(since: datetime, until: datetime) -> list[dict]:
    rows = []
    for path in takes_in(since, until):
        try:
            found = stay(path)
        except (OSError, ValueError, KeyError) as error:
            print(f'  {path.name}: not read ({error})', file=sys.stderr)
            continue
        if found is not None:
            rows.append(found)
    return rows


def totals(rows: list[dict]) -> dict[str, float]:
    seconds = sum(r['seconds'] for r in rows)
    return {
        'stays': len(rows),
        'minutes': seconds / 60,
        'kills': sum(r['kills'] for r in rows),
        'per_minute': sum(r['kills'] for r in rows) / (seconds / 60) if seconds else 0.0,
        'standing': sum(r['standing'] for r in rows) / seconds if seconds else 0.0,
    }


def show(rows: list[dict], names: dict[int, str]) -> None:
    print(f'{"take":24} {"level":22} {"s":>6} {"kills":>5} {"seen":>5} {"k/min":>6} {"cast":>5} {"move":>5} '
          f'{"stand":>5} {"long":>5} {"tp":>4} herald')  # fmt: skip
    for r in rows:
        minutes = r['seconds'] / 60
        print(
            f'{r["take"]:24} {names.get(r["area"], str(r["area"]))[:22]:22} {r["seconds"]:6.0f} {r["kills"]:5d} '
            f'{r["seen"]:5d} {r["kills"] / minutes:6.1f} {r["casting"] / r["seconds"]:5.0%} '
            f'{r["moving"] / r["seconds"]:5.0%} {r["standing"] / r["seconds"]:5.0%} {r["longest"]:5.1f} '
            f'{r["teleports"]:4d} {"tier " + str(r["herald"]) if r["herald"] is not None else ""}'
        )
    t = totals(rows)
    print(f'\n{t["stays"]} stays, {t["minutes"]:.1f} min in the levels, {t["kills"]} kills: '
          f'{t["per_minute"]:.1f} kills a minute; standing {t["standing"]:.0%} of the time')  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    now = datetime.now().astimezone()
    parser.add_argument('--since', type=local, default=now - timedelta(hours=2))
    parser.add_argument('--until', type=local, default=now)
    parser.add_argument('--against', nargs=2, type=local, metavar=('SINCE', 'UNTIL'))
    args = parser.parse_args()
    names = level_names()
    rows = rows_in(args.since, args.until)
    show(rows, names)
    if args.against:
        before, after = totals(rows_in(*args.against)), totals(rows)
        print(f'\nagainst {args.against[0]:%H:%M}-{args.against[1]:%H:%M}: {before["per_minute"]:.1f} -> '
              f'{after["per_minute"]:.1f} kills a minute ({before["stays"]} -> {after["stays"]} stays)')  # fmt: skip


if __name__ == '__main__':
    main()
