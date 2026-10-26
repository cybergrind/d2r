"""Explicit, resumable Traderie pull of the loop's materials for `pricing.knowledge.commodity_market`.

Writes `pricing/raw/traderie/appraisal-commodities-<date>/<item id>-page0.json`, the format the commodity importer
reads, plus `status.json`. Only page 0 (the 50 newest listings) answers without a Traderie login: page 1 is HTTP 401
(2026-10-03, 2026-10-25). Asks per whole stack are divided by the amount on import (`market.normalize_listing`).

    python3 pricing/tools/collect_commodities.py --collect            # the default materials
    python3 pricing/tools/collect_commodities.py --collect "Ort Rune"  # named items only
then, offline:
    uv run --offline python -m pricing.knowledge.commodity_market
    uv run --offline python -m pricing.knowledge rebuild
"""

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for runs by path
from pricing.knowledge.material_items import MATERIAL_CATALOG
from pricing.knowledge.refresh import RateLimited, atomic_json, fetch_json
from pricing.knowledge.scope import in_scope
from pricing.tools.traderie import listings_url


ROOT = Path(__file__).resolve().parents[2]
# What the KP_6 loop picks (inventory_tracking/loot/materials.py): statues, essences, the token, keys, shards; runes
# below the ladder's lowest rung (Lem); every gem grade but the plain one.
LOOP_MISC = {name for name in MATERIAL_CATALOG if re.search(r'essence|token|^key of|shard', name)} | {
    "talic's anguish",
    "korlic's pain",
    "madawc's ire",
    "bul-kathos' nightmare",
    "worusk's end",
}
LOW_RUNES = [
    'El',
    'Eld',
    'Tir',
    'Nef',
    'Eth',
    'Ith',
    'Tal',
    'Ral',
    'Ort',
    'Thul',
    'Amn',
    'Sol',
    'Shael',
    'Dol',
    'Hel',
    'Io',
    'Lum',
    'Ko',
    'Fal',
]
GEM = re.compile(r'^(Chipped|Flawed|Flawless|Perfect) (Amethyst|Diamond|Emerald|Ruby|Sapphire|Topaz|Skull)$')
SPACING_S = 5  # 46 buy-side calls at 5 s were fine (pricing-refresh skill, 2026-10-09)


def targets(catalog: list[dict], names: list[str]) -> list[dict]:
    """Catalog rows of the named items, or of the default materials."""
    if names:
        wanted = {name.casefold() for name in names}
        return [item for item in catalog if item['name'].casefold() in wanted]
    runes = {f'{rune} Rune' for rune in LOW_RUNES}
    return [
        item
        for item in catalog
        if (
            item['type'] == 'misc'
            and item['name'].casefold() in LOOP_MISC
            and MATERIAL_CATALOG.get(item['name'].casefold()) == str(item['id'])
        )
        or (item['type'] == 'runes' and item['name'] in runes)
        or (item['type'] == 'gems' and GEM.match(item['name']))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('names', nargs='*', help='catalog names; default the loop materials')
    parser.add_argument('--collect', action='store_true', help='fetch (without it: list the targets and cached pages)')
    parser.add_argument('--date', default=datetime.now(UTC).strftime('%Y%m%d'))
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'pricing/data/appraisal-traderie-catalog.json').read_text())['items']
    items = sorted(targets(catalog, args.names), key=lambda i: (i['type'], i['name']))
    directory = ROOT / f'pricing/raw/traderie/appraisal-commodities-{args.date}'
    status: dict[str, Any] = {'state': 'complete', 'started_at': datetime.now(UTC).isoformat(), 'targets': {}}
    for item in items:
        path = directory / f'{item["id"]}-page0.json'
        if path.exists() or not args.collect:
            print(f'{item["name"]}: {"cached" if path.exists() else "not fetched"}')
            continue
        directory.mkdir(parents=True, exist_ok=True)
        url = listings_url(item['id'], 0)
        try:
            response = fetch_json(url)
            if not isinstance(response.get('listings'), list):
                raise OSError(f'missing listings array: {url}')
        except (OSError, ValueError) as error:
            status.update(
                state='rate_limited' if isinstance(error, RateLimited) else 'stopped_on_source_error',
                error=str(error),
                failed_target=item['name'],
                stopped_at=datetime.now(UTC).isoformat(),
            )
            atomic_json(directory / 'status.json', status)
            sys.exit(f'{item["name"]}: {error}')
        listings = response['listings']
        verified = sum(1 for listing in listings if in_scope(listing))
        atomic_json(
            path,
            {
                'name': item['name'],
                'type': item['type'],
                'source': url,
                'fetched_at': datetime.now(UTC).isoformat(),
                'listings': listings,
                'response': response,
                'scope_counts': {'verified': verified, 'rejected': len(listings) - verified},
            },
        )
        status['targets'][item['name']] = {'listings': len(listings), 'in_scope': verified}
        atomic_json(directory / 'status.json', status)
        print(f'{item["name"]}: {len(listings)} listings, {verified} in scope', flush=True)
        time.sleep(SPACING_S)
    if args.collect:
        status['finished_at'] = datetime.now(UTC).isoformat()
        atomic_json(directory / 'status.json', status)


if __name__ == '__main__':
    main()
