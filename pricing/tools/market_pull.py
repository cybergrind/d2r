"""Paced, resumable bulk pull of Traderie asks for the whole catalog (explicit online maintenance).

Raw pages land in pricing/raw/traderie/pull-<date>/<catalog id>-p<page>.json; state.json records
finished items, so a rerun continues where a rate limit or Ctrl+C stopped it. One request at a
time with a fixed delay: the unpaced three-thread refresh hit HTTP 429 on 2026-09-23.

    uv run python pricing/tools/market_pull.py [--types uniques,sets] [--delay 3] [--limit N]
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from pricing.knowledge.market import normalize_listing, summarize
from pricing.knowledge.refresh import API, RateLimited, RequestRejected, atomic_json, fetch_json


ROOT = Path(__file__).resolve().parents[2]
ORDER = ('runes', 'gems', 'misc', 'uniques', 'sets', 'charms', 'crafted', 'runewords', 'base')
# Affixed families: one catalog item holds every magic/rare roll, so a few pages say nothing.
DEEP = frozenset(
    {'Small Charm', 'Large Charm', 'Grand Charm', 'Jewel', 'Ring', 'Amulet', 'Circlet', 'Coronet', 'Tiara', 'Diadem'}
)


def targets(catalog, types):
    rank = {category: index for index, category in enumerate(ORDER)}
    items = [i for i in catalog['items'] if i['type'] in types]
    return sorted(items, key=lambda i: (i['name'] not in DEEP or i['type'] != 'base', rank[i['type']], i['name']))


def pull_item(item, directory, currencies, *, pages, deep_pages, sellers, delay, fetch=fetch_json, sleep=time.sleep):
    """Fetch pages until enough scoped priced sellers, an empty page or the page cap; returns a summary."""
    rows, fetched = [], 0
    cap = deep_pages if item['name'] in DEEP else pages
    reason = 'page_cap'
    for page in range(cap):
        path = directory / f'{item["id"]}-p{page}.json'
        if path.exists():
            response = json.loads(path.read_text())
        else:
            try:
                response = fetch(f'{API}/listings?item={item["id"]}&page={page}')
            except RateLimited:
                raise
            except RequestRejected:
                if page == 0:
                    raise
                reason = 'login_required'  # since 2026-10-03 pages past the first answer HTTP 401 to guests
                break
            response['_pulled_at'] = datetime.now(UTC).isoformat()
            atomic_json(path, response)
            fetched += 1
            sleep(delay)
        listings = response.get('listings') or []
        rows.extend(
            normalize_listing(
                row,
                name=item['name'],
                category=item['type'],
                source=f'{API}/listings?item={item["id"]}&page={page}',
                observed_at=response.get('_pulled_at'),
                currencies=currencies,
            )
            for row in listings
        )
        if not listings:
            reason = 'source_exhausted'
            break
        if item['name'] not in DEEP and summarize(rows)['priced_sellers'] >= sellers:
            reason = 'seller_target_met'
            break
    return {
        'name': item['name'],
        'type': item['type'],
        'reason': reason,
        'fetched': fetched,
        'scoped': sum(row['scope_status'] == 'verified' for row in rows),
        'priced_sellers': summarize(rows)['priced_sellers'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / f'pricing/raw/traderie/pull-{datetime.now(UTC):%Y%m%d}')
    parser.add_argument('--types', default=','.join(ORDER))
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--deep-pages', type=int, default=1)
    parser.add_argument('--sellers', type=int, default=12)
    parser.add_argument('--delay', type=float, default=3.0)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / 'pricing/data/appraisal-traderie-catalog.json').read_text())
    ladder = json.loads((ROOT / 'pricing/data/wp-f-ladder.json').read_text())
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    state_path = args.out / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    todo = [i for i in targets(catalog, args.types.split(',')) if str(i['id']) not in state][: args.limit]
    print(f'{len(todo)} items to pull, {len(state)} done → {args.out}', flush=True)
    for index, item in enumerate(todo, 1):
        try:
            done = pull_item(
                item,
                args.out,
                currencies,
                pages=args.pages,
                deep_pages=args.deep_pages,
                sellers=args.sellers,
                delay=args.delay,
            )
        except RateLimited as error:
            print(f'RATE LIMITED at {item["name"]}: {error}', flush=True)
            return 3
        except (RequestRejected, OSError, ValueError, KeyError) as error:
            print(f'{item["name"]}: failed: {error}', flush=True)
            if isinstance(error, RequestRejected):
                return 4
            continue
        state[str(item['id'])] = done
        atomic_json(state_path, state)
        print(
            f'[{index}/{len(todo)}] {item["type"]} {item["name"]}: {done["reason"]}, '
            f'{done["scoped"]} scoped, {done["priced_sellers"]} priced sellers',
            flush=True,
        )
    print('DONE', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
