"""Explicit online catalog/market maintenance, never imported by offline lookup."""

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from pricing.knowledge.market import (
    import_cache,
    normalize_facets,
    normalize_listing,
    property_values,
    scope_status,
    summarize,
)


def reconcile_listing_properties(row):
    """Reparse source fields before publishing a cached observation."""
    row['properties'] = property_values(row.get('raw_properties', []))
    row['scope_status'] = scope_status(row['properties'])
    normalize_facets(row)


API = 'https://traderie.com/api/diablo2resurrected'


USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'


class RequestRejected(OSError):
    """HTTP rejection or challenge: stop rather than retrying a denied request."""


class RateLimited(RequestRejected):
    """Server rate limit: stop this maintenance batch."""


def _fetch_response(url):
    with NamedTemporaryFile() as header_file:
        response = subprocess.run(
            [
                'curl',
                '--write-out',
                '\n%{http_code}',
                '--dump-header',
                header_file.name,
                '-sSL',
                '-A',
                USER_AGENT,
                '--max-time',
                '40',
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # curl includes proxy/redirect headers; only the final response applies.
        headers = {}
        for line in Path(header_file.name).read_text().splitlines():
            if line.startswith('HTTP/'):
                headers = {}
            elif ':' in line:
                name, value = line.split(':', 1)
                headers[name.strip().lower()] = value.strip()
    body, status = response.stdout.rsplit('\n', 1)
    return body, status, headers


def fetch_json(url):
    for attempt in range(3):
        try:
            body, status, headers = _fetch_response(url)
            if status == '429' or (status != '200' and 'Error 1015' in body):
                retry = headers.get('retry-after', 'unavailable')
                raise RateLimited(f'HTTP {status}; Retry-After: {retry}; stop batch: {url}')
            if headers.get('cf-mitigated', '').lower() == 'challenge':
                ray = headers.get('cf-ray', 'unavailable')
                raise RequestRejected(f'HTTP {status}; Cloudflare challenge; Ray ID: {ray}; stop batch: {url}')
            if status != '200':
                raise RequestRejected(f'HTTP {status}; request rejected: {url}')
            return json.loads(body)
        except RequestRejected:
            raise
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            if attempt == 2:
                raise OSError(f'JSON request failed: {url}: {error}') from error
            time.sleep(2**attempt)
    raise RuntimeError('unreachable')


def refresh_item(item, fetch, currencies, *, page_cap=4, seller_target=10, previous=None):
    if previous and previous.get('terminal_reason') in ('source_exhausted', 'seller_target_met'):
        return previous
    job = dict(previous or {'item': item, 'pages': [], 'rows': [], 'next_page': 0})
    job['rows'] = list(job['rows'])
    job['pages'] = list(job['pages'])
    for page in range(job['next_page'], page_cap):
        try:
            response = fetch(page)
            listings = response['listings']
        except (OSError, ValueError, KeyError) as error:
            reason = 'fetch_error'
            if isinstance(error, RequestRejected):
                reason = 'request_rejected'
            if isinstance(error, RateLimited):
                reason = 'rate_limited'
            job.update(terminal_reason=reason, error=str(error))
            break
        now = datetime.now(UTC).isoformat()
        job['pages'].append(
            {
                'page': page,
                'observed_at': now,
                'listings': len(listings),
                'sha256': hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest(),
            }
        )
        job['rows'].extend(
            normalize_listing(
                row,
                name=item['name'],
                category=item['type'],
                source=f'{API}/listings?item={item["id"]}&page={page}',
                observed_at=now,
                currencies=currencies,
            )
            for row in listings
        )
        job['next_page'] = page + 1
        job['terminal_reason'] = 'page_cap'
        if not listings:
            job['terminal_reason'] = 'source_exhausted'
            break
        if summarize(job['rows'])['priced_sellers'] >= seller_target:
            job['terminal_reason'] = 'seller_target_met'
            break
    job['scoped_observations'] = sum(row['scope_status'] == 'verified' for row in job['rows'])
    job['priced_sellers'] = summarize(job['rows'])['priced_sellers']
    return job


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def catalog_census(directory):
    path = directory / 'appraisal-traderie-catalog.json'
    previous = json.loads(path.read_text()) if path.exists() else {'items': [], 'types': {}}
    for category in ('uniques', 'sets', 'runes', 'gems', 'misc', 'base', 'runewords', 'charms', 'crafted'):
        if previous['types'].get(category, {}).get('complete'):
            continue
        items = []
        pages = 0
        error = None
        try:
            for page in range(100):
                response = fetch_json(f'{API}/items?type={category}&page={page}')
                chunk = response['items']
                pages += 1
                if not chunk:
                    break
                items.extend(chunk)
            else:
                error = 'page_cap'
        except (OSError, ValueError, KeyError) as exc:
            error = str(exc)
        previous['items'] = [i for i in previous['items'] if i['type'] != category] + items
        previous['types'][category] = {
            'pages': pages,
            'count': len(items),
            'complete': error is None,
            'error': error,
            'observed_at': datetime.now(UTC).isoformat(),
        }
        atomic_json(path, previous)
    return previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--refresh-limit', type=int, default=30)
    parser.add_argument('--offline-import', action='store_true')
    parser.add_argument('--pages', type=int, default=4)
    args = parser.parse_args()
    directory = args.root / 'pricing/data'
    catalog = (
        json.loads((directory / 'appraisal-traderie-catalog.json').read_text())
        if args.offline_import
        else catalog_census(directory)
    )
    rows, manifest = import_cache(args.root, catalog['items'])
    ladder = json.loads((directory / 'wp-f-ladder.json').read_text())
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    demand = list(json.loads((directory / 'wp-a-variants/index.json').read_text()))
    expanded = directory / 'appraisal-demand.json'
    if expanded.exists():
        data = json.loads(expanded.read_text())
        demand.extend(r['name'] for r in data.get('rows', []))
    demand = [label.lower() for label in demand]
    covered = {r['catalog_id'] for r in rows if r['scope_status'] == 'verified'}
    watch = []
    for item in catalog['items']:
        demanded = any(item['name'].lower() in label for label in demand)
        watch.append(
            {
                'id': str(item['id']),
                'name': item['name'],
                'type': item['type'],
                'demanded': demanded,
                'cached_scoped': str(item['id']) in covered,
            }
        )
    watch.sort(key=lambda item: (item['cached_scoped'], not item['demanded'], item['type'], item['name']))
    atomic_json(
        directory / 'appraisal-watchlist.json',
        {
            'schema_version': 1,
            'items': watch,
            'coverage_note': 'Catalog census plus demand mentions; combinatorial rolls require pattern rules.',
        },
    )
    jobs_path = directory / 'appraisal-refresh-jobs.json'
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else {}
    targets = [i for i in watch if not i['cached_scoped'] and i['demanded']][: args.refresh_limit]

    def run(item):
        return item['id'], refresh_item(
            item,
            lambda page: fetch_json(f'{API}/listings?item={item["id"]}&page={page}'),
            currencies,
            page_cap=args.pages,
            previous=jobs.get(item['id']),
        )

    if not args.offline_import:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for offset in range(0, len(targets), 3):
                limited = False
                for iid, job in pool.map(run, targets[offset : offset + 3]):
                    jobs[iid] = job
                    atomic_json(jobs_path, jobs)
                    limited = limited or job['terminal_reason'] in ('rate_limited', 'request_rejected')
                    print(f'{job["item"]["name"]}: {job["terminal_reason"]}', flush=True)
                if limited:
                    break
    for job in jobs.values():
        for row in job['rows']:
            row['conversion'].update(snapshot_id='pricing/data/wp-f-ladder.json', snapshot_date=ladder['_meta']['date'])
            rows.append(row)
    property_dictionary = {}
    for row in rows:
        reconcile_listing_properties(row)
        for prop in row.get('raw_properties', []):
            key = str(prop['property_id'])
            entry = property_dictionary.setdefault(key, {'id': key, 'labels': set(), 'types': set()})
            if prop.get('property'):
                entry['labels'].add(prop['property'])
            entry['types'].add(prop['type'])
    atomic_json(
        directory / 'appraisal-properties.json',
        {
            'schema_version': 1,
            'properties': {
                key: {'id': key, 'labels': sorted(entry['labels']), 'types': sorted(entry['types'])}
                for key, entry in property_dictionary.items()
            },
            'source': 'Observed Traderie listing raw_properties; labels preserved verbatim, no guessed skill IDs.',
        },
    )
    output = directory / 'appraisal-market.jsonl'
    temporary = output.with_suffix('.jsonl.tmp')
    temporary.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows))
    temporary.replace(output)
    manifest.update(
        refresh_jobs={iid: {k: v for k, v in job.items() if k != 'rows'} for iid, job in jobs.items()},
        total_observations=len(rows),
        catalog_types=catalog['types'],
    )
    covered = {r['catalog_id'] for r in rows if r['scope_status'] == 'verified'}
    for item in watch:
        item['cached_scoped'] = item['id'] in covered
        item['coverage_status'] = 'observed' if item['cached_scoped'] else 'unresolved'
    classes = []
    bases = json.loads((directory / 'wp-b-prices.json').read_text())
    for slug, entry in bases.items():
        if not isinstance(entry, dict):
            continue
        for bucket in entry.get('buckets', {}):
            classes.append(
                {
                    'id': slug + '/' + bucket,
                    'name': entry.get('name', slug),
                    'conditions': bucket,
                    'source': 'pricing/data/wp-b-prices.json',
                    'evidence_status': 'legacy_bucket_requires_strict_revalidation',
                }
            )
    for filename in ('wp-h-jewels-charms.json', 'wp-i-uniques-misc.json'):
        for key, entry in json.loads((directory / filename).read_text()).items():
            if key.startswith('_') or not isinstance(entry, dict):
                continue
            classes.append(
                {
                    'id': key,
                    'name': entry.get('name', key),
                    'conditions': entry.get('bucket_def', entry.get('roll_bucket')),
                    'source': 'pricing/data/' + filename,
                    'evidence_status': 'legacy_bucket_requires_strict_revalidation',
                }
            )
    atomic_json(directory / 'appraisal-watchlist.json', {'schema_version': 1, 'items': watch, 'classes': classes})
    atomic_json(
        directory / 'appraisal-trade-catalog.json',
        {
            'schema_version': 1,
            'rows': [
                {
                    'id': 'catalog-' + str(i['id']),
                    'kind': 'catalog',
                    'name': i['name'],
                    'category': i['type'],
                    'catalog_id': str(i['id']),
                    'source': API + '/items?type=' + i['type'],
                    'observed_at': catalog['types'][i['type']]['observed_at'],
                    'market_coverage': 'observed' if str(i['id']) in covered else 'unresolved',
                    'description': i.get('description'),
                }
                for i in catalog['items']
            ],
        },
    )
    manifest['covered_catalog_items'] = len(covered)
    manifest['scope_counts_all'] = {
        status: sum(r['scope_status'] == status for r in rows) for status in ('verified', 'unknown', 'rejected')
    }
    old_manifest = directory / 'appraisal-market-manifest.json'
    if old_manifest.exists():
        previous_hold = json.loads(old_manifest.read_text()).get('maintenance_hold')
        if previous_hold:
            manifest['maintenance_hold'] = previous_hold
    atomic_json(old_manifest, manifest)


if __name__ == '__main__':
    main()
