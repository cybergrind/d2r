from pricing.knowledge.assessment.comparables import evaluate


def row(date, price, properties=None):
    return {
        'listing_id': 'same',
        'seller_id': 'seller',
        'observed_at': date,
        'name': 'Ring',
        'rarity': 'magic',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': properties or {'520': 10},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'ask_ist': price,
        'source': 'fixture',
    }


def contract():
    return {
        'name': 'Ring',
        'rarity': 'magic',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'520': 10},
        'policy': 'affixed',
    }


def test_latest_listing_snapshot_replaces_old_price_regardless_of_input_order():
    old, new = row('2026-09-18T12:00:00Z', 1), row('2026-09-24T12:00:00Z', 4)
    for rows in ([old, new], [new, old]):
        result = evaluate(contract(), rows)
        assert result['summary']['median_ist'] == 4
        assert result['accepted'] == [new]
        assert 'superseded' in result['rejected'][0]['reasons'][0].lower()


def test_new_incompatible_modifiers_do_not_resurrect_old_matching_listing():
    result = evaluate(contract(), [row('2026-09-18', 1), row('2026-09-24', 4, {'520': 20})])
    assert not result['accepted']


def test_separate_listing_ids_still_give_one_cheapest_vote_per_seller():
    old, new = row('2026-09-18', 1), row('2026-09-24', 4)
    new['listing_id'] = 'another'
    assert evaluate(contract(), [old, new])['summary']['median_ist'] == 1


def test_date_precision_and_undated_rows_do_not_invent_recency():
    from pricing.knowledge.assessment.observations import superseded_rows

    assert superseded_rows([row('2026-09-24', 1), row('2026-09-24T12:00:00Z', 4)]) == set()
    assert superseded_rows([row(None, 1), row('2026-09-24', 4)]) == set()
    assert superseded_rows([row('2026-09-24T15:00:00+03:00', 1), row('2026-09-24T12:01:00Z', 4)]) == {0}
