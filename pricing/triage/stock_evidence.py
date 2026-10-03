"""Recover omitted stock flags from existing raw caches, without market requests.

Traderie's seller help (checked 2026-10-03) describes stock as available inventory
from which buyers request subsets; it does not define the displayed ask's unit:
https://traderie.com/hypershot/getting-started/seller
"""

import json
from pathlib import Path


def restore(rows, root):
    sources = {}
    for row in rows:
        if row.get('category') in ('runes', 'gems') and row.get('amount') != 1 and 'listing_stock' not in row:
            source = row.get('source', '')
            if source.startswith('pricing/raw/') and '..' not in Path(source).parts:
                sources.setdefault(source, set()).add(str(row.get('listing_id')))
    flags = {}
    for source, ids in sources.items():
        path = root / source
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text())
        except OSError, ValueError:
            continue
        listings = document if isinstance(document, list) else document.get('listings', [])
        for listing in listings:
            key = str(listing.get('id'))
            if key in ids and type(listing.get('stock')) is bool:
                flags[source, key] = listing['stock']
    result = []
    for row in rows:
        key = row.get('source'), str(row.get('listing_id'))
        if key in flags:
            row = row | {'listing_stock': flags[key]}
        if row.get('listing_stock') is True and row.get('amount') != 1:
            row = row | {'unit_policy': 'ambiguous', 'ask_ist': None}
        result.append(row)
    return result
