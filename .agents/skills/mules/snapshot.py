"""Dump every captured item with its triage verdict, one TSV row per item, for mule planning.

uv run --offline python .agents/skills/mules/snapshot.py > "$SCRATCH/items.tsv"

Columns: loc, captured (MM-DD), verdict, median_ist, keep_ist, rarity, name, base, WxH,
copies (open placements with the same name; uniques/sets/runewords only), stats, notes, loop_card.
loc is S1..S5 for shared tabs, otherwise <character>/<inv|sta|cub|equ|mer>.
loop_card: what the KP_6 loop would do with the item were it a loop find (the one assessment entry point at CARD,
loot/assess.py; identify/service.py `card_of`, the owned copies from the collection less this one): `keep K5`,
`vendor K8`... (2026-10-23). It is the loop's rule, not a stash ruling: the mules skill's own rules decide what is
dropped (never the last copy of a unique or set). A runeword reads `n/a`: the loot layers judge it as its plain base
(rca/2026-10-23 D12), so the column says nothing of one.
"""

import collections
import json
import re
import sqlite3
import sys

from inventory_tracking.identify.service import card_of
from pricing.api import triage


DATABASE = 'inventory_tracking/runs/collection/collection.sqlite'
D2DATA = 'pricing/raw/d2data'
NOISE = (
    'Durability',
    'Maximum durability',
    'Base weapon speed',
    'Secondary',
    'Minimum damage',
    'Maximum damage',
    'Armor movement',
    'Minimum throw',
    'Maximum throw',
    'Base cold',
    'Defense:',
    'Shield blocking',
    '+50% Damage to Undead (inherent',
)
NAMED = ('unique', 'set')


def main():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """select p.owner, p.container, p.tab, p.seen_at, i.* from placements p join items i using(fingerprint)
           where p.gone_at is null and p.container != 'materials' and not (p.owner = 'shared' and p.tab > 5)
           order by p.owner, p.container, p.tab, i.rarity, i.name"""
    ).fetchall()
    copies = collections.Counter(key(r) for r in rows if key(r))
    sizes = base_sizes()
    print('loc\tcaptured\tverdict\tmedian_ist\tkeep_ist\trarity\tname\tbase\tsize\tcopies\tstats\tnotes\tloop_card')
    for r in rows:
        observation = json.loads(r['observation'])
        try:
            result = triage(observation)
            judged = result['triage']
        except Exception as error:  # one undecodable item must not hide the rest
            result, judged = None, {'verdict': 'ERR', 'reason': repr(error)}
        print_row(r, judged, card(observation, result, r), copies, sizes)


def card(observation, result, row) -> str:
    """The CARD outcome and rule of one item ('vendor K8'), `n/a` for a runeword or an item it cannot judge."""
    if row['runeword'] or result is None:
        return 'n/a'
    found = card_of(observation, result)
    return f'{found["outcome"]} {found["rule"]}' if found is not None else 'n/a'


def print_row(r, triage, judged, copies, sizes):
    band = triage.get('band') or triage.get('reference_band') or {}
    median = band.get('median_ist') if isinstance(band, dict) else None
    median = round(median, 2) if median is not None else ''
    loc = f'S{r["tab"]}' if r['owner'] == 'shared' else f'{r["owner"]}/{r["container"][:3]}'
    flags = ('eth ' if r['ethereal'] else '') + (f'{r["sockets"]}os ' if r['sockets'] else '')
    name = r['runeword'] or r['name'] or ''
    stats = '; '.join(clean(s) for s in json.loads(r['stat_lines']) if not s.startswith(NOISE))
    notes = str(triage.get('reason') or '')[:120]
    notes += f' OWN:{str(triage["own_use"])[:80]}' if triage.get('own_use') else ''
    notes += f' DEM:{str(triage["demand"])[:120]}' if triage.get('demand') else ''
    print(
        loc,
        r['seen_at'][5:10],
        triage['verdict'],
        median,
        triage.get('keep_ist'),
        r['rarity'],
        name,
        f'{flags}{r["base_name"]}',
        size(r, sizes),
        copies.get(key(r), ''),
        stats[:260],
        notes,
        judged,
        sep='\t',
    )


def base_sizes():
    """Base code → (width, height); the collection DB stores no item sizes yet."""
    sizes = {}
    for table in ('armor', 'weapons', 'misc'):
        with open(f'{D2DATA}/{table}.json') as handle:
            for code, base in json.load(handle).items():
                if base.get('invwidth'):
                    sizes[code] = (base['invwidth'], base['invheight'])
    return sizes


def size(row, sizes):
    width, height = (row['width'], row['height']) if row['width'] else sizes.get(row['base_code'], ('?', '?'))
    return f'{width}x{height}'


def key(row):
    if row['runeword']:
        return f'RW:{row["runeword"]}'
    return row['name'] if row['rarity'] in NAMED and row['name'] else None


def clean(line):
    return re.sub(r' \[T\d+; T1: [^\]]*\]| \(\d[^)]*\)', '', line)


if __name__ == '__main__':
    sys.exit(main())
