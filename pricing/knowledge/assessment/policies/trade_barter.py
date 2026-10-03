"""Explicitly reviewed item-for-item asking interest, never an Ist conversion."""


def validate_barter(review):
    ids = review.get('barter_evidence_ids', [])
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate barter evidence')
    rows = {r['id']: r for r in review['market_evidence']}
    candidate_ids = set(review['default_evidence_ids']) if review['default_status'] == 'candidate' else set()
    for band in review['bands']:
        if band['status'] == 'candidate':
            candidate_ids.update(band['evidence_ids'])
    if set(ids) - rows.keys() or set(ids) - candidate_ids:
        raise ValueError('Unreviewed barter evidence or unsupported premium claim')
    for identifier in ids:
        row = rows[identifier]
        prices = row.get('prices')
        if row.get('ask_ist') is not None or not isinstance(prices, list) or not prices:
            raise ValueError('Invalid barter asking terms')
        for price in prices:
            if (
                not isinstance(price, dict)
                or not price.get('item_id')
                or not price.get('name')
                or type(price.get('quantity')) is not int
                or price['quantity'] <= 0
                or type(price.get('group')) is not int
                or price['group'] < 0
            ):
                raise ValueError('Incomplete barter asking terms')
    return set(ids)
