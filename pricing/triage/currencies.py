"""Recover gem-denominated asks from dated, scoped, rune-priced gem listings."""

from collections import defaultdict
from statistics import median

from pricing.knowledge.market import convert_groups, valid_positive
from pricing.triage.bands import eligible, latest_rows, timestamp


def apply_gem_quotes(rows, rune_rates):
    groups = defaultdict(list)
    for row in latest_rows(rows):
        prices = row.get('prices', [])
        if (
            row.get('category') == 'gems'
            and eligible(row)
            and valid_positive(row.get('ask_ist'))
            and row.get('seller_id')
            and timestamp(row.get('observed_at'))
            and prices
            and all(p.get('type') == 'runes' for p in prices)
        ):
            groups[row['name'].lower()].append(row)
    quotes = {}
    for name, members in groups.items():
        votes = {}
        for row in members:
            seller = str(row['seller_id'])
            votes[seller] = min(votes.get(seller, float('inf')), row['ask_ist'])
        if len(votes) >= 3:
            quotes[name] = {
                'ist': median(votes.values()),
                'sellers': len(votes),
                'observed_at': max(timestamp(r['observed_at']) for r in members),
                'oldest_observation': min(timestamp(r['observed_at']) for r in members),
                'listing_ids': sorted(str(r['listing_id']) for r in members),
                'sources': sorted({r['source'] for r in members if r.get('source')}),
                'basis': 'scoped rune asks per gem; one minimum ask per seller',
            }
    rates = rune_rates | {name: q['ist'] for name, q in quotes.items()}
    result = []
    for row in rows:
        used = {p.get('name', '').lower() for p in row.get('prices', [])} & quotes.keys()
        if used and eligible(row):
            ask, conversion = convert_groups(row['prices'], rates)
            if ask is not None and row['unit_policy'] == 'stack_total':
                ask /= row['amount']
            conversion.update(
                rune_snapshot='pricing/data/wp-f-ladder.json',
                gem_quotes={name: quotes[name] for name in sorted(used)},
            )
            row = row | {'ask_ist': ask, 'conversion': conversion}
        result.append(row)
    return result
