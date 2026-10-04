"""Import paid clean-base variants from scoped comparisons, never pooled names."""

from collections import defaultdict

from inventory_tracking.items.metadata import metadata
from pricing.triage.adapters import from_listing
from pricing.triage.bands import band_for, eligible, latest_rows
from pricing.triage.base_comparisons import no_better_modifiers, no_worse_modifiers
from pricing.triage.engine import matches
from pricing.triage.rule_index import candidates, compile_index
from pricing.triage.variants import profile_for, scoped_bucket


FACETS = ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers']


def clean_modifiers(item, base, policy):
    """Reject affixed/filled-item signatures and internally inconsistent quality."""
    modifiers = item.get('base_modifiers')
    if not isinstance(modifiers, dict):
        return False
    allowed = dict.fromkeys(policy.get('compare_staffmods', {}), (1, 3))
    if item['rarity'] == 'superior':
        allowed['937'] = (10, 15)
        if base['category'] == 'weapons':
            allowed['423'] = (1, 3)
    elif item['base_ed'] != 0:
        return False
    if base['type'] == 'ashd':
        # The shared projection expands one all-resistance roll into four
        # equal components. Those copies are not additional base modifiers.
        if '441' in modifiers:
            modifiers = {
                p: v for p, v in modifiers.items() if p not in ('401', '426', '427', '428') or v != modifiers['441']
            }
        allowed |= {'441': (5, 45), '510': (10, 65), '423': (15, 121)}
        if ('510' in modifiers) != ('423' in modifiers):
            return False
        if '441' in modifiers and '510' in modifiers:
            return False
    # Native Amazon skill automods; labels verified in appraisal-properties.json.
    if base['type'] == 'abow':
        allowed['454'] = (1, 3)
    if base['type'] in ('aspe', 'ajav'):
        allowed['456'] = (1, 3)
    return all(
        p in allowed and type(value) is int and allowed[p][0] <= value <= allowed[p][1]
        for p, value in modifiers.items()
    )


def compile_market_bases(rows, rules, policies, utility, *, keep_ist, excluded_words):
    bases = {b['code']: b for b in metadata()['bases'].values()}
    recipes = defaultdict(set)
    for entry in utility:
        details = entry.get('details', {})
        if details.get('legality') == 'verified_type_and_capacity' and details['runeword'] not in excluded_words:
            recipes[entry['base_code'], entry['sockets']].add(details['runeword'])
    existing = compile_index([r for r in rules if r.get('bucket') and not r.get('imported_market_base')])
    groups, items = defaultdict(list), {}
    by_name = defaultdict(list)
    for row in latest_rows(rows):
        if not eligible(row) or row.get('amount') != 1:
            continue
        item = from_listing(row)
        base = bases.get(item.get('base_code'))
        if (
            item['category'] != 'base'
            or not base
            or item['name'].casefold() != base['name'].casefold()
            or type(item['ethereal']) is not bool
            or item['rarity'] not in ('normal', 'superior')
            or type(item['sockets']) is not int
            or not 2 <= item['sockets'] <= base['max_sockets']
            or not item['empty_sockets']
            or item['socket_contents'] != 'empty'
            or not recipes.get((base['code'], item['sockets']))
            or not clean_modifiers(item, base, profile_for(item, policies))
            or any(matches(item, rule) for rule in candidates(item, existing))
        ):
            continue
        facet = scoped_bucket('market-backed', item, FACETS)
        if facet is None:
            continue
        key = item['name'], facet
        groups[key].append(row)
        items[key] = item
        by_name[item['name']].append((row, item))
    result = []
    for key, members in sorted(groups.items()):
        item = items[key]
        policy = profile_for(item, policies)
        conditions = {field: item[field] for field in FACETS if field != 'base_modifiers'}
        comparison = conditions | {'base_modifiers': {'in': no_better_modifiers(item, policy)}}
        members = [row for row, candidate in by_name[item['name']] if matches(candidate, {'conditions': comparison})]
        band = band_for('base', item['name'], members)
        # Two independent sellers establish a paid variant worth CHECK.
        # The engine still requires three for thin liquidity and SELL (slow).
        if band['sellers'] < 2 or band['q1_ist'] < keep_ist:
            continue
        conditions['base_modifiers'] = {'in': no_worse_modifiers(item, policy)}
        sources = sorted({row.get('source', 'scoped cached listing') for row in members})
        result.append(
            {
                'category': 'base',
                'name': item['name'],
                'bucket': 'market-backed',
                'conditions': conditions,
                'comparison_pattern': {'conditions': comparison},
                'source': sources[0],
                'sources': sources,
                'runewords': sorted(recipes[item['base_code'], item['sockets']]),
                'evidence': {'sellers': band['sellers'], 'q1_ist': band['q1_ist'], 'observed_at': band['observed_at']},
                'imported_market_base': True,
            }
        )
    return result
