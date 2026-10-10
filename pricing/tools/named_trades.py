#!/usr/bin/env python3
"""Portable trade summary of named items (uniques and sets) from Traderie Recent Trades pulls.

  uv run --offline python pricing/tools/named_trades.py pricing/raw/traderie/recent-named-<date> \
      [--out pricing/data/named-trades.json]

Reads the files traderie_trades.mjs saved (one per catalog id), names each item from the trade record and
writes per item: trades on the newest page, the span of days they cover, trades per day, trades in the last
30 and 90 days, how many were priced in runes/gems, and the lower-quartile and median paid in Ist (dated
ladder pricing/data/wp-f-ladder.json). The loot-filter generator reads this file as its trade evidence.
"""

import datetime
import glob
import json
import statistics
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from traderie_trades import item_name, load_json, trades


def summarise(directory):
    now = datetime.datetime.now(datetime.UTC)
    items = []
    for path in sorted(glob.glob(f'{directory}/*.json')):
        document = load_json(path)
        rows = trades(document, now)
        paid = sorted(r['paid'] for r in rows if r['paid'] is not None)
        span = max(rows[-1]['days_ago'], 1) if rows else None
        items.append(
            {
                'name': item_name(document) or Path(path).stem,
                'catalog_id': Path(path).stem,
                'pulled_at': document.get('pulled_at'),
                'trades': len(rows),
                'days_span': span,
                'per_day': round(len(rows) / span, 3) if rows else 0.0,
                'last': rows[0]['when'] if rows else None,
                'last_30d': sum(r['days_ago'] <= 30 for r in rows),
                'last_90d': sum(r['days_ago'] <= 90 for r in rows),
                'priced': len(paid),
                'q1_ist': round(paid[len(paid) // 4], 3) if paid else None,
                'median_ist': round(statistics.median(paid), 3) if paid else None,
            }
        )
    return items


def main(argv):
    directory = argv[0]
    out = Path(argv[argv.index('--out') + 1]) if '--out' in argv else Path('pricing/data/named-trades.json')
    items = summarise(directory)
    document = {
        'source': 'Traderie Recent Trades (offers accepted and completed), scoped SC/NL/PC/RotW, newest page per item',
        'read_with': 'pricing/tools/traderie_trades.mjs; summarised by pricing/tools/named_trades.py',
        'date': datetime.date.today().isoformat(),
        'unit': 'Ist = 1 via pricing/data/wp-f-ladder.json; prices in other items are unpriced',
        'items': items,
    }
    out.write_text(json.dumps(document, indent=1) + '\n')
    print(f'{len(items)} items → {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
