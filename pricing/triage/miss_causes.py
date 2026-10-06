"""Actionable replay misses, ranked by independent sellers within each category."""

from collections import Counter, defaultdict


def cause(item, result, tables):
    if result.get('verdict') == 'self':
        return 'own_use_only'
    if result.get('sale_mode') == 'accumulate':
        return 'save_for_bulk_lot'
    if result.get('roll_comparison'):
        return 'roll_comparison'
    band = result.get('band') or {}
    if band.get('q1_ist') is not None:
        return 'insufficient_sellers' if band.get('sellers', 0) < 3 else 'below_keep_price'
    if item['category'] == 'base':
        if item.get('rarity') is None:
            return 'base_rarity_missing'
        if item['rarity'] not in ('normal', 'superior'):
            return 'base_quality_unsupported'
        if item.get('socket_contents') == 'filled':
            return 'base_socket_contents_filled'
        if item.get('socket_contents') != 'empty':
            return 'base_socket_contents_missing'
        if type(item.get('ethereal')) is not bool:
            return 'base_ethereal_missing'
        enhancement = item.get('base_ed')
        if enhancement is None:
            return 'base_enhancement_missing'
        if type(enhancement) not in (int, float) or not 0 <= enhancement <= 15:
            return 'base_enhancement_invalid'
        if item['rarity'] == 'normal' and enhancement != 0:
            return 'base_quality_conflicting'
        if item.get('base_modifiers') is None:
            return 'base_modifiers_unreadable'
        from inventory_tracking.items.metadata import metadata_generation
        from pricing.triage.adapters import bases_by_code
        from pricing.triage.market_bases import clean_modifiers

        base = bases_by_code(metadata_generation()).get(item.get('base_code'))
        if base and not clean_modifiers(item, base, {}):
            return 'base_native_modifiers_conflicting'
        from pricing.triage.engine import matches
        from pricing.triage.rule_index import candidates

        rows = candidates(item, tables['rule_index']) if 'rule_index' in tables else tables['rules']['rows']
        matched = any(r.get('bucket') and matches(item, r) for r in rows)
        return 'base_variant_price_missing' if matched else 'base_bucket_missing'
    if item['category'] in ('magic', 'rare', 'crafted'):
        return 'no_paid_pattern'
    return 'no_matched_price'


class MissCauses:
    def __init__(self):
        self.groups = {}

    def add(self, row, item, result, tables):
        key = item['category'], item.get('family') or item.get('name'), cause(item, result, tables)
        group = self.groups.setdefault(key, {'listings': 0, 'sellers': set(), 'examples': []})
        group['listings'] += 1
        if row.get('seller_id'):
            group['sellers'].add(str(row['seller_id']))
        if len(group['examples']) < 3:
            group['examples'].append(
                {
                    'listing_id': row['listing_id'],
                    'name': item['name'],
                    'reason': result['reason'],
                    'ask_ist': row['ask_ist'],
                    'source': row.get('source'),
                }
            )
        return key

    def report(self, selected):
        votes = Counter(key for key in selected if key is not None)
        categories = defaultdict(list)
        for (category, family, reason), group in self.groups.items():
            categories[category].append(
                {
                    'family': family,
                    'cause': reason,
                    'distinct_sellers': len(group['sellers']),
                    'seller_votes': votes[category, family, reason],
                    'listings': group['listings'],
                    'examples': group['examples'],
                }
            )
        return {
            category: sorted(groups, key=lambda g: (-g['distinct_sellers'], -g['listings'], str(g['family'])))
            for category, groups in sorted(categories.items())
        }
