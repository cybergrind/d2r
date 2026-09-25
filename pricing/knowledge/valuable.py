"""Build an offline unique/set keep-and-review watchlist from cached research.

Guide tiers describe demand, not this economy's prices. Conditions and source
ages stay attached; build mentions alone are not high resale value.
"""

import hashlib
import json
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

from pricing.knowledge.index import normalize_name
from pricing.knowledge.market import summarize


GUIDE_URL = 'https://maxroll.gg/d2/items/valuable-unique-set-items'


class GuideTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def build_watchlist(root):
    root = Path(root)
    inputs = {}

    def read(relative):
        data = (root / relative).read_bytes()
        inputs[relative] = hashlib.sha256(data).hexdigest()
        return data.decode()

    parser = GuideTable()
    parser.feed(read('pricing/raw/mr/items__valuable-unique-set-items.html'))
    guide = {normalize_name(r[0]): r for r in parser.rows if len(r) >= 4 and r[1] in ('High', 'Med', 'Low')}
    if not guide:
        raise ValueError('Valuable-items source table missing')
    curated = json.loads(read('pricing/data/wp-i-uniques-misc.json'))
    local = {normalize_name(v['name']): v for k, v in curated.items() if k.startswith(('UQ-', 'ST-')) and v.get('name')}
    demand = defaultdict(set)
    contexts = defaultdict(list)
    for row in json.loads(read('pricing/data/appraisal-demand.json'))['rows']:
        if row.get('build') and row.get('details', {}).get('recommended'):
            key = normalize_name(row['name'])
            demand[key].add(row['build'])
            if row.get('variant') != 'Guide mention':
                contexts[key].append(
                    {
                        k: row.get(k)
                        for k in ('build', 'variant', 'side', 'slot', 'original_label', 'source_id', 'source_locator')
                    }
                )
    definitions = json.loads(read('pricing/data/appraisal-definitions.json'))['rows']
    market_by_name = defaultdict(list)
    for line in read('pricing/data/appraisal-market.jsonl').splitlines():
        row = json.loads(line)
        if row.get('rarity') in ('unique', 'set'):
            market_by_name[normalize_name(row['name'])].append(row)
    rows = []
    for definition in definitions:
        if definition.get('rarity') not in ('unique', 'set'):
            continue
        name = definition['name']
        key = normalize_name(name)
        old = guide.get(key)
        current = local.get(key, {})
        tier = current.get('our_tier', '')
        builds = sorted(demand[key])
        market_reference = summarize(market_by_name[key])
        market_priority = market_reference['priced_sellers'] >= 5 and (market_reference['median_ist'] or 0) >= 8
        notable = (old and old[1] in ('High', 'Med')) or any(t in tier for t in ('High', 'HR')) or market_priority
        if not notable and not builds:
            continue
        rows.append(
            {
                'name': name,
                'kind': 'value_watch',
                'rarity': definition['rarity'],
                'date': '2026-09-24',
                'source': {'path': 'pricing/data/wp-i-uniques-misc.json', 'source_date': curated['_meta']['date']},
                'details': {
                    'priority': 'valuable_candidate' if notable else 'build_demand',
                    'local_tier': tier or None,
                    'local_conditions': current.get('threshold'),
                    'roll_bucket': current.get('roll_bucket'),
                    'guide_tier': old[1] if old else None,
                    'guide_conditions': old[2] if old else None,
                    'stat_priority': old[3] if old else None,
                    'guide_source': {'url': GUIDE_URL, 'source_date': '2024-03-06'},
                    'builds': builds,
                    'build_contexts': contexts[key],
                    'build_count': len(builds),
                    'nonladder_ask_reference': market_reference,
                    'market_priority': market_priority,
                    'caveat': 'Keep/review priority, not a guaranteed resale value. '
                    'Guide ranks are early-ladder 2024; local research is dated.',
                },
            }
        )
    rows.sort(
        key=lambda r: (
            r['details']['priority'] != 'valuable_candidate',
            not any(t in (r['details']['local_tier'] or '') for t in ('High', 'HR')),
            -(r['details']['nonladder_ask_reference']['median_ist'] or 0)
            if r['details']['nonladder_ask_reference']['priced_sellers'] >= 5
            else 0,
            -r['details']['build_count'],
            r['name'],
        )
    )
    return {
        'schema_version': 1,
        'inputs': inputs,
        'rows': rows,
        'coverage': {
            'guide_trade_rows': len(guide),
            'watch_items': len(rows),
            'valuable_candidates': sum(r['details']['priority'] == 'valuable_candidate' for r in rows),
            'ranking': 'Keep priority: local High/HR, then mixed-roll NL median asks (5+ sellers), then build count.',
        },
    }


def main():
    root = Path(__file__).resolve().parents[2]
    result = build_watchlist(root)
    (root / 'pricing/data/appraisal-value-watch.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = [
        '# Unique/set items to review first',
        '',
        'Generated from cached research, 2026-09-24. This is a keep/review priority list, not a price ranking.',
        'Numerical report estimates use verified Softcore / Non-Ladder / PC / RotW asks only.',
        'The Maxroll source is dated 2024-03-06 and describes early ladder; its tiers are demand context only.',
        'Local qualitative tiers are dated 2026-09-18; conditions and rolls can change value.',
        '',
        f'{result["coverage"]["valuable_candidates"]} valuable candidates; '
        f'{result["coverage"]["watch_items"]} total watch items including build demand.',
        '',
        '| Item | Local research tier | Builds | Guide priority (2024) |',
        '| --- | --- | ---: | --- |',
    ]
    for row in result['rows']:
        d = row['details']
        if d['priority'] == 'valuable_candidate':
            lines.append(
                f'| {row["name"]} | {d["local_tier"] or "unranked"} | '
                f'{d["build_count"]} | {d["guide_tier"] or "not listed"} |'
            )
    lines.extend(
        [
            '',
            f'Source: [{GUIDE_URL}]({GUIDE_URL}); local WP-I and appraisal-demand research.',
            'Full conditions and build names: pricing/data/appraisal-value-watch.json.',
        ]
    )
    (root / 'pricing/knowledge/VALUABLE_ITEMS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(result['coverage']))


if __name__ == '__main__':
    main()
