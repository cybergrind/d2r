"""Explicit, resumable runeword collection. Defaults to cached coverage only."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from pricing.knowledge.refresh import API, RateLimited, atomic_json, fetch_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--pages', type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    directory = root / 'pricing/raw/traderie/runeword-refresh'
    directory.mkdir(exist_ok=True)
    items = json.loads((root / 'pricing/data/appraisal-traderie-catalog.json').read_text())['items']
    items = sorted((i for i in items if i['type'] == 'runewords'), key=lambda i: i['name'])
    status = {'started_at': datetime.now(UTC).isoformat(), 'items': {}, 'state': 'complete'}
    for item in items:
        count = 0
        for page in range(args.pages):
            slug = item['name'].lower().replace(' ', '-')
            path = directory / f'{slug}-page{page}.json'
            if path.exists():
                response = json.loads(path.read_text())['response']
            elif not args.collect:
                break
            else:
                url = f'{API}/listings?item={item["id"]}&page={page}'
                try:
                    response = fetch_json(url)
                    if not isinstance(response.get('listings'), list):
                        raise OSError('Missing listings array')
                except (OSError, ValueError) as exc:
                    status.update(
                        state='rate_limited' if isinstance(exc, RateLimited) else 'fetch_error',
                        error=str(exc),
                        stopped_at=datetime.now(UTC).isoformat(),
                        item=item['name'],
                        page=page,
                    )
                    atomic_json(directory / 'status.json', status)
                    print(status, flush=True)
                    return
                atomic_json(
                    path,
                    {'item': item, 'observed_at': datetime.now(UTC).isoformat(), 'source': url, 'response': response},
                )
                time.sleep(0.4)
            count += len(response['listings'])
            if not response['listings']:
                break
        status['items'][item['name']] = count
        atomic_json(directory / 'status.json', status)
        print(f'{item["name"]}: {count} cached observations', flush=True)
    print(f'{len(items)} runeword catalog entries processed', flush=True)


if __name__ == '__main__':
    main()
