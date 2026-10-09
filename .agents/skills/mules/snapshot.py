"""Dump every captured item with its triage verdict, one TSV row per item, for mule planning.

uv run --offline python .agents/skills/mules/snapshot.py > "$SCRATCH/items.tsv"

Columns: loc, captured (MM-DD), verdict, median_ist, keep_ist, rarity, name, base, WxH,
copies (open placements with the same name; uniques/sets/runewords only), stats, notes.
loc is S1..S5 for shared tabs, otherwise <character>/<inv|sta|cub|equ|mer>.
"""

import collections
import json
import re
import sqlite3
import sys

from pricing.triage import runtime


DATABASE = 'inventory_tracking/runs/collection/collection.sqlite'
D2DATA = 'pricing/raw/d2data'
NOISE = (
    'Durability', 'Maximum durability', 'Base weapon speed', 'Secondary', 'Minimum damage',
    'Maximum damage', 'Armor movement', 'Minimum throw', 'Maximum throw', 'Base cold', 'Defense:',
    'Shield blocking', '+50% Damage to Undead (inherent',
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
    print('loc\tcaptured\tverdict\tmedian_ist\tkeep_ist\trarity\tname\tbase\tsize\tcopies\tstats\tnotes')
    for r in rows:
        try:
            triage = runtime.retrieve(json.loads(r['observation']))['triage']
        except Exception as error:  # one undecodable item must not hide the rest
            triage = {'verdict': 'ERR', 'reason': repr(error)}
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
            loc, r['seen_at'][5:10], triage['verdict'], median, triage.get('keep_ist'), r['rarity'], name,
            f'{flags}{r["base_name"]}', size(r, sizes), copies.get(key(r), ''), stats[:260], notes,
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
