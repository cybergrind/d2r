"""The KP_6 loop's trading: what it picked up to identify, what the appraisal said, what it sold and for how much, the
time it cost, and the repairs the gold paid for (routes/lower-kurast-loop-plan.md §15).

The player, 2026-10-17: "you need to measure our trading efficiency time/gold. what we pickup, what we sell it for".

From serve's probe.logs (stdlib only):

- **identified**: `Macro: identify: appraised <quality> <base> (<class>) at (x, y): <verdict>` (macros/junk.py), by
  base and verdict; the tries from the tome's `identify: N of M items identified` and, since the town visit
  (2026-10-18), Cain's `Cain: N of M items identified` (logwords.py `IDENTIFIED`);
- **sold**: `Macro: shop: sold the item <class> at (x, y) for <gold> gold: <quality> <base> (<class>)` (macros/shop.py),
  the full stacks' runes and gems apart from the junk;
- **time**: the `identify` legs, and the `scrolls and keys` legs that sold junk (the visit at a game's end is made for
  the sales; at a game's start it also buys keys and scrolls), from `Macro: Loop: game N, <leg>` to the next leg; since
  2026-10-18 one `town visit` leg (macros/visit.py), its stops' seconds from its `trade session done` line
  (`(cain C, stash S, jamella J, halbu H, walk W)`): Cain's as the identify time, Jamella's as the visit's;
- **gold**: per sale, per hour of play (the games' seconds, `games.py`), per second of trade time; and each repair's
  cost (`Macro: repair: the staff A -> B charges (of C), gold X -> Y`) against it.
- **shopping** (the player, 2026-10-17: "we visited shop just to purchase keys/tps ... measure shopping time
  efficiently to keep overall chest per hour optimal"): every `scrolls and keys` visit, bare (keys and scrolls only) or
  with sales, its seconds; and the visits to Cain (`identify` legs); seconds a game for each;
- **by kind** (the player, 2026-10-17: "we need to have some metric for picking up items for trade: type vs space vs
  time to trade to gold per trade/per occupied cell"): each item identified, by its quality and type, with its cells
  (loot/data/sizes.json), its pickup seconds (from the `pickup:` line that first names it to its `picked up` line),
  its share of its game's identify leg and of the visit that sold it, its verdict and its sale's gold. Per kind: gold
  a trade, a cell, a second; and the **payback**: the seconds its gold buys back as the staff's Teleport charges
  (`--saved` seconds a stay with a charge, over the charges a stay with charges spends, at the repairs' gold a
  charge) over the seconds it cost. Under 1 the kind costs the loop time; leave it on the ground.

    python3 .agents/skills/d2-loop-watch/tools/trade.py [--since 'YYYY-MM-DD HH:MM'] [--until ...] [--items 15]
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import games  # ruff: ignore[module-import-not-at-top-of-file] - the skill's own tool, beside this one
from logwords import (  # ruff: ignore[module-import-not-at-top-of-file]
    AFTER,
    APPRAISED,
    IDENTIFIED,
    LEG,
    LOOP_OFF,
    MACRO_STOPPED,
    PICKED,
    PICKUP,
    REPAIRED,
    SOLD,
    TELEPORT,
    UNSOLD,
    VISIT_STOPS,
    stamp,
)


ROOT = HERE.parents[3]
SIZES = ROOT / 'inventory_tracking' / 'loot' / 'data' / 'sizes.json'
METADATA = ROOT / 'inventory_tracking' / 'items' / 'data' / 'item_metadata.json'
GOLD_A_CHARGE = 111469 / 64  # the repair of 10:33 on 2026-10-17: 5 -> 69 charges for 111,469 gold
CHARGES_A_STAY = 7.5  # Teleport casts a game with charges after the repair of 10:33 on 2026-10-17 (8 games)
SAVED = 7.0  # seconds a stay with a staff charge is shorter (speed.py, 06:51-10:51 on 2026-10-17: 30.6 -> 23.6, n 23)
PREFIXES = ('Magic ', 'Rare ', 'Superior ', 'Socketed ', 'Set ', 'Unique ', 'Low Quality ', 'Crafted ')

JUNK_NAME = re.compile(r'^(magic|rare|set|unique|crafted|white) ')


def local(text: str) -> datetime:
    return datetime.strptime(text, '%Y-%m-%d %H:%M')


def read(directory: Path, since: datetime, until: datetime) -> dict:
    """One session's trading: identified items, sales, repairs, the trade legs' seconds."""
    found: dict = {'appraised': [], 'sold': [], 'unsold': 0, 'repairs': [], 'identify_s': 0.0, 'selling_s': 0.0,
                   'tries': [0, 0], 'gained': 0}  # fmt: skip
    vendor: Counter[str] = Counter()  # the classes appraised `vendor` and not sold yet: a sale of one is junk's
    found['items'], found['teleports'] = [], []  # each item traded (`Trade`), the Teleport casts of each game
    found['visits'] = []  # each shop visit: (seconds, items sold)
    game: dict = {}  # the game in progress: its picks' seconds by base, its items, its legs' seconds
    asked: dict[str, datetime] = {}  # the label a pickup line named, and when first

    def settle() -> None:
        if not game:
            return
        found['teleports'].append(game['teleports'])
        items = game['items']
        if items:
            share_identify = game['identify'] / len(items)
            sold = [i for i in items if i['gold'] is not None]
            share_sell = game['selling'] / len(sold) if sold else 0.0
            for item in items:
                picks = game['picks'].get(item['base'], [])
                item['pickup'] = picks.pop(0) if picks else None
                item['identify'] = share_identify
                item['sell'] = share_sell if item['gold'] is not None else 0.0
            found['items'] += items
        game.clear()

    leg: tuple[str, datetime] | None = None
    sold_in_leg = False
    sold_count = [0]  # the items the visit in progress sold
    stops: dict[str, float] = {}  # the town visit's stops' seconds (its `trade session done` line)

    def close(at: datetime) -> None:
        if leg is None:
            return
        seconds = (at - leg[1]).total_seconds()
        if leg[0] == 'identify':
            found['identify_s'] += seconds
            game['identify'] = game.get('identify', 0.0) + seconds
        elif leg[0] == 'scrolls and keys':
            found['visits'].append((seconds, sold_count[0]))
            if sold_in_leg:
                found['selling_s'] += seconds
                game['selling'] = game.get('selling', 0.0) + seconds
        elif leg[0] == 'town visit':
            # One leg for Cain, the stash, Jamella, Halbu: each stop by its own seconds
            cain, jamella = stops.get('cain'), stops.get('jamella')
            if cain is not None:
                found['identify_s'] += cain
                game['identify'] = game.get('identify', 0.0) + cain
            if jamella is not None:
                found['visits'].append((jamella, sold_count[0]))
                if sold_in_leg:
                    found['selling_s'] += jamella
                    game['selling'] = game.get('selling', 0.0) + jamella

    for line in (directory / 'probe.log').read_text(errors='replace').splitlines():
        at = stamp(line)
        if at is None or at < since or at > until:
            continue
        if (m := LEG.search(line)) is not None:
            close(at)
            leg, sold_in_leg, sold_count[0] = (m.group(2).strip(), at), False, 0
            stops.clear()
            if game.get('number') != m.group(1):
                settle()
                game.update(number=m.group(1), picks=defaultdict(list), items=[], identify=0.0, selling=0.0,
                            teleports=0)  # fmt: skip
                asked.clear()
        elif TELEPORT in line:
            if game:
                game['teleports'] += 1
        elif (m := PICKUP.search(line)) is not None:
            asked.setdefault(m.group(1), at)
        elif (m := PICKED.search(line)) is not None:
            label, began = m.group(1), asked.pop(m.group(1), at)
            for prefix in PREFIXES:
                label = label.removeprefix(prefix)
            if game:
                game['picks'][label].append((at - began).total_seconds())
        elif LOOP_OFF in line or MACRO_STOPPED in line:
            close(at)
            leg = None
        elif (m := APPRAISED.search(line)) is not None:
            name = m.group(3) or f'item {m.group(1)}'
            found['appraised'].append((m.group(2) or '?', name, m.group(5)))
            if game:
                game['items'].append({'quality': m.group(2) or '?', 'base': name, 'txt': m.group(1) or m.group(4),
                                      'verdict': m.group(5), 'gold': None})  # fmt: skip
            if m.group(5) == 'vendor':
                vendor[m.group(1) or m.group(4)] += 1
        elif (m := IDENTIFIED.search(line)) is not None:
            found['tries'][0] += int(m.group(1))
            found['tries'][1] += int(m.group(2))
        elif (m := SOLD.search(line)) is not None:
            what = m.group(3) or f'item {m.group(1)}'
            gold = int(m.group(2)) if m.group(2) is not None else None
            junk = bool(JUNK_NAME.match(what)) or vendor[m.group(1)] > 0
            if vendor[m.group(1)] > 0:
                vendor[m.group(1)] -= 1
            if junk and game:
                match = next((i for i in game['items'] if i['txt'] == m.group(1) and i['gold'] is None
                              and i['verdict'] == 'vendor'), None)  # fmt: skip
                if match is not None:
                    match['gold'] = gold if gold is not None else 0
            found['sold'].append((what, gold, junk))
            sold_count[0] += 1
            sold_in_leg = sold_in_leg or junk
        elif (m := AFTER.search(line)) is not None:
            found['gained'] += int(m.group(2)) - int(m.group(1))
        elif UNSOLD.search(line):
            found['unsold'] += 1
        elif (m := VISIT_STOPS.search(line)) is not None:
            seconds = zip(('cain', 'jamella'), m.groups(), strict=True)
            stops.update({name: float(value) for name, value in seconds if value != '-'})
        elif (m := REPAIRED.search(line)) is not None:
            found['repairs'].append((int(m.group(3)) - int(m.group(4)), m.group(1), m.group(2)))
    close(until)
    settle()
    return found


def kinds(items: list[dict], seconds_a_gold: float) -> list[str]:
    """The table by kind (quality and item type): the module text's last point."""
    sizes = json.loads(SIZES.read_text())['sizes']
    bases = json.loads(METADATA.read_text())['bases']
    rows: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        base = bases.get(str(item['txt'])) or {}
        rows[f'{item["quality"]} {base.get("type", "?")}'].append(item)
    lines = [
        f'{"kind":14} {"n":>3} {"cells":>5} {"pick s":>6} {"id s":>5} {"sell s":>6} {"sold":>5} {"gold/sale":>9} '
        f'{"gold/item":>9} {"gold/cell":>9} {"gold/s":>7} {"payback":>7}'
    ]
    for kind, found in sorted(rows.items(), key=lambda kv: -len(kv[1])):
        n = len(found)
        cells = sum(math.prod(sizes.get(str(i['txt']), (1, 1))) for i in found) / n
        picks = [i['pickup'] for i in found if i['pickup'] is not None]
        pick = sum(picks) / len(picks) if picks else 0.0
        ident = sum(i['identify'] for i in found) / n
        sell = sum(i['sell'] for i in found) / n
        sold = [i['gold'] for i in found if i['gold'] is not None]
        gold = sum(sold) / n
        spent = pick + ident + sell
        payback = gold * seconds_a_gold / spent if spent else 0.0
        lines.append(
            f'{kind:14} {n:3} {cells:5.1f} {pick:6.1f} {ident:5.1f} {sell:6.1f} {len(sold) / n:5.0%} '
            f'{(sum(sold) / len(sold) if sold else 0):9,.0f} {gold:9,.0f} {gold / cells:9,.0f} '
            f'{gold / spent if spent else 0:7,.0f} {payback:7.2f}'
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--since', type=local)
    parser.add_argument('--until', type=local)
    parser.add_argument('--items', type=int, default=15, help='the bases listed, the most identified first')
    parser.add_argument('--saved', type=float, default=SAVED, help='seconds a stay with a staff charge is shorter')
    args = parser.parse_args()
    until = args.until or datetime.now()
    since = args.since or until - timedelta(hours=2)

    total: dict = defaultdict(list)
    seconds = identify_s = selling_s = 0.0
    unsold, tried, done, gained = 0, 0, 0, 0
    played: list = []
    for directory in games.sessions(argparse.Namespace(sessions=None, since=since)):
        one = read(directory, since, until)
        for key in ('appraised', 'sold', 'repairs', 'items', 'teleports', 'visits'):
            total[key] += one[key]
        identify_s += one['identify_s']
        selling_s += one['selling_s']
        unsold += one['unsold']
        gained += one['gained']
        done, tried = done + one['tries'][0], tried + one['tries'][1]
        played += [g for g in games.read(directory, since, until)[0] if g.seconds is not None and g.end == 'next']
    seconds = sum(g.seconds for g in played)
    hours = seconds / 3600 if seconds else 0.0

    print(f'window {since:%Y-%m-%d %H:%M} .. {until:%H:%M}: {len(played)} whole games, {seconds / 60:.0f} min of play')
    appraised = total['appraised']
    verdicts = Counter(v for _, _, v in appraised)
    print(f'\nidentified: {done} of {tried} tried (the tome or Cain); appraised {len(appraised)}: '
          + ', '.join(f'{v} {n}' for v, n in verdicts.most_common()))  # fmt: skip
    by_base: dict[str, Counter] = defaultdict(Counter)
    for quality, name, verdict in appraised:
        by_base[f'{quality} {name}'][verdict] += 1
    for name, counts in sorted(by_base.items(), key=lambda kv: -sum(kv[1].values()))[: args.items]:
        print(f'  {sum(counts.values()):3}  {name:40} ' + ', '.join(f'{v} {n}' for v, n in counts.most_common()))

    sold = total['sold']
    junk = [(what, gold) for what, gold, is_junk in sold if is_junk]
    stacks = [(what, gold) for what, gold, is_junk in sold if not is_junk]
    priced = [gold for _, gold in junk if gold is not None]
    print(f'\nsold: {len(junk)} junk items' + (f' ({sum(priced):,} gold for the {len(priced)} priced, '
          f'{sum(priced) / len(priced):,.0f} a sale)' if priced else '') + f'; {len(stacks)} full-stack items; '
          f'{unsold} could not be sold; {gained:,} gold carried more after the visits')  # fmt: skip
    for what, gold in sorted(junk, key=lambda wg: -(wg[1] or 0))[: args.items]:
        print(f'  {gold if gold is not None else "?":>7}  {what}')

    visits = total['visits']
    bare = [sec for sec, n in visits if n == 0]
    selling = [sec for sec, n in visits if n > 0]
    games_n = len(played) or 1
    print(f'\nshopping: {len(visits)} visits to Jamella, {len(bare)} bare ({sum(bare):.0f} s, '
          f'{sum(bare) / len(bare) if bare else 0:.1f} s each), {len(selling)} with sales ({sum(selling):.0f} s, '
          f'{sum(n for _, n in visits) / len(selling) if selling else 0:.1f} items each); '
          f'{sum(sec for sec, _ in visits) / games_n:.1f} s a game at Jamella, '
          f'{identify_s / games_n:.1f} s at Cain')  # fmt: skip
    trade_s = identify_s + selling_s
    print(f'\ntime: identify {identify_s:.0f} s, the visits that sold {selling_s:.0f} s; '
          f'{trade_s / len(played) if played else 0:.1f} s a game')  # fmt: skip
    if hours:
        print(f'gold: {gained / hours:,.0f} an hour of play from sales; '
              + (f'{gained / trade_s:,.0f} a second of trade time' if trade_s else 'no trade time'))  # fmt: skip
    charged = [n for n in total['teleports'] if n]
    a_stay = sum(charged) / len(charged) if len(charged) >= 3 else CHARGES_A_STAY  # the window's, or the last known
    spent_gold = sum(cost for cost, _, _ in total['repairs'])
    charges_bought = sum(int(b) - int(a) for _, a, b in total['repairs'] if b.isdigit())
    a_charge = spent_gold / charges_bought if charges_bought > 0 else GOLD_A_CHARGE
    seconds_a_gold = args.saved / a_stay / a_charge if a_stay else 0.0
    print(f'\nby kind (payback: the seconds its gold buys as Teleport charges over the seconds it cost; '
          f'{a_charge:,.0f} gold a charge, {a_stay:.1f} charges a stay with them, {args.saved:g} s saved a stay: '
          f'{1 / seconds_a_gold if seconds_a_gold else 0:,.0f} gold a second):')  # fmt: skip
    for line in kinds(total['items'], seconds_a_gold):
        print(f'  {line}')
    repairs = total['repairs']
    if repairs:
        spent = sum(cost for cost, _, _ in repairs)
        print(f'repairs: {len(repairs)} for {spent:,} gold (' + '; '.join(f'{a} -> {b} charges' for _, a, b in repairs)
              + f'); the sales paid {gained / spent:.0%} of it' if spent else '')  # fmt: skip
    elif gained:
        print(
            'repairs: none in the window; a repair of 69 charges cost 111,469 gold (10:33 on 2026-10-17): '
            f'the sales paid {gained / 111469:.0%} of one'
        )


if __name__ == '__main__':
    main()
