"""Compact endgame demand hints compiled offline from explicit guide gear variants."""

import re
from collections import defaultdict


CATEGORIES = {'unique': 'uniques', 'set': 'sets', 'runeword': 'runewords'}
EXCLUDED = re.compile(r'starter|budget|hardcore|levell?ing|guide mention|main alternatives', re.I)


def compile_demand(rows, watches=()):
    evidence = defaultdict(list)
    for row in rows:
        details = row.get('details', {})
        variant = row.get('variant', '')
        if (
            not variant
            or EXCLUDED.search(variant)
            or '/variants/' not in row.get('source_locator', '')
            or row.get('source_id') != 'pricing/data/wp-a-builds.json'
            or details.get('recommended') is not True
            or details.get('resolution_status') != 'resolved'
        ):
            continue
        label = row.get('original_label', '').casefold()
        ethereal = False if 'non-ethereal' in label else True if 'ethereal' in label else None
        record = {
            'build': row['build'],
            'variant': variant,
            'side': row.get('side'),
            'slot': row.get('slot'),
            'ethereal': ethereal,
            'source': row['source_id'],
            'locator': row['source_locator'],
            'original_label': row.get('original_label', ''),
        }
        if row.get('category') in CATEGORIES:
            key = CATEGORIES[row['category']] + '/' + row['name'].casefold()
            if record not in evidence[key]:
                evidence[key].append(record)
        for watch in watches:
            if watch['name'].casefold() == row['name'].casefold() or watch.get('rarity') not in CATEGORIES:
                continue
            name = re.escape(watch['name'].casefold())
            insert = (
                re.search(r'(?<!\w)' + name + r'(?!\w)', label)
                if 'facet' in watch['name'].casefold()
                else re.search(r'(?<!\w)' + name + r'\s+(?:jewel|socketed)\b', label)
            )
            if insert:
                insert_key = CATEGORIES[watch['rarity']] + '/' + watch['name'].casefold()
                evidence[insert_key].append(record | {'ethereal': None, 'kind': 'socket_insert'})
    for watch in watches:
        details = watch.get('details', {})
        tier = details.get('local_tier') or ''
        if watch.get('rarity') not in CATEGORIES or not (
            details.get('priority') == 'valuable_candidate' or re.search(r'\b(?:Low|Mid|High|HR)\b', tier, re.I)
        ):
            continue
        key = CATEGORIES[watch['rarity']] + '/' + watch['name'].casefold()
        evidence[key].append(
            {
                'kind': 'value_watch',
                'ethereal': None,
                'source': 'pricing/data/appraisal-value-watch.json',
                'date': watch.get('date'),
                'priority': details.get('priority'),
                'local_tier': details.get('local_tier'),
                'conditions': details.get('local_conditions') or details.get('guide_conditions'),
            }
        )
    return dict(evidence)


def demand_for(item, evidence):
    key = str(item.get('category')) + '/' + str(item.get('name', '')).casefold()
    from pricing.triage.engine import matches

    return [
        r
        for r in evidence.get(key, [])
        # A name-level watch is research context, not a reviewed use for this copy.
        # Its prose may describe a different mode, ethereal variant or perfect roll.
        if r.get('kind') != 'value_watch'
        and (r['ethereal'] is None or r['ethereal'] is item.get('ethereal'))
        and matches(item, {'conditions': r.get('base_conditions', {})})
    ]


def cohorts_without_demand(tables):
    """Review list only: lack of a demand hint never creates a VENDOR rule."""
    rows = []

    def visit(node, item):
        if 'children' in node:
            for child in node['children'].values():
                visit(child, item)
            return
        band = node['band']
        price = band.get('q1_ist')
        if (
            price is not None
            and tables['rules']['keep_ist'] <= price < 1
            and band['sellers'] >= 10
            and not demand_for(item, tables.get('demand', {}))
        ):
            rows.append(
                {
                    **item,
                    'bucket': band['bucket'],
                    'q1_ist': price,
                    'sellers': band['sellers'],
                    'date': band['observed_at'],
                }
            )

    for band in tables['bands'].values():
        for ethereal, node in band.get('named_cohorts', {}).items():
            visit(
                node,
                {
                    'category': band['category'],
                    'name': band['name'],
                    'ethereal': {'true': True, 'false': False, 'null': None}[ethereal],
                },
            )
    return sorted(rows, key=lambda row: (row['name'], str(row['ethereal']), row['bucket']))
