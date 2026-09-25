from datetime import date

from pricing.knowledge.assessment.maintenance.market_readiness import audit


def row(**changes):
    return {
        'name': 'Vampire Gaze',
        'category': 'uniques',
        'rarity': 'unique',
        'listing_id': 'one',
        'seller_id': 'seller',
        'observed_at': '2026-09-24',
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'ask_ist': 1,
        'base_code': 'fixture',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {},
        **changes,
    }


def test_readiness_separates_missing_facets_from_scope_and_does_not_price():
    incomplete = row(listing_id='two', base_code=None, ethereal=None, sockets=None, socket_contents='unknown')
    rows = [row(), incomplete, row(listing_id='foreign', scope_status='rejected')]
    result = audit(rows, today=date(2026, 9, 24))
    item = result['items'][0]
    assert item['scoped_observations'] == 2
    assert item['structurally_ready'] == 1
    assert item['gaps'] == {'base_code': 1, 'ethereal': 1, 'sockets': 1, 'socket_contents': 1}
    assert 'estimate_ist' not in item
    assert incomplete['socket_contents'] == 'unknown'


def test_duplicate_and_superseded_snapshots_do_not_inflate_readiness():
    old = row(observed_at='2026-09-23', ethereal=None)
    latest = row()
    item = audit([old, latest, dict(latest)], today=date(2026, 9, 24))['items'][0]
    assert item['scoped_observations'] == 1
    assert item['structurally_ready'] == 1
    assert item['gaps'] == {}


def test_stale_and_malformed_rows_retain_specific_research_gaps():
    rows = [row(observed_at='2026-01-01'), row(listing_id='bad', sockets=True, ask_ist=float('nan'), seller_id=None)]
    item = audit(rows, today=date(2026, 9, 24))['items'][0]
    assert item['structurally_ready'] == 0
    assert item['gaps']['stale'] == 1
    assert item['gaps']['sockets'] == 1
    assert item['gaps']['price'] == 1
    assert item['gaps']['seller'] == 1


def test_supported_filled_armor_is_ready_without_inventing_modifier_or_price_evidence():
    from inventory_tracking.items.metadata import metadata

    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Grim Helm')
    filled = row(base_code=base, sockets=1, socket_contents='filled', properties={'934': 'Um Rune'})
    item = audit([filled], today=date(2026, 9, 24))['items'][0]
    assert item['structurally_ready'] == 1
    assert item['gaps'] == {}
    assert 'estimate_ist' not in item
    for payload in (None, 'Jewel', 'Um Rune, Um Rune', '', 'Um Rune, Unknown'):
        changed = {**filled, 'properties': {'934': payload}}
        result = audit([changed], today=date(2026, 9, 24))['items'][0]
        assert result['structurally_ready'] == 0
        assert result['gaps']['filled_socket_comparison'] == 1


def test_readiness_respects_destination_and_unsupported_stacked_flags():
    from inventory_tracking.items.metadata import metadata

    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Ettin Axe')
    candidate = row(name='Rune Master', base_code=base, sockets=3, socket_contents='filled')
    for payload, ready in [('Zod Rune, Shael Rune', 1), ('Perfect Ruby', 0), ('Zod Rune, Zod Rune', 0)]:
        item = audit([{**candidate, 'properties': {'934': payload}}], today=date(2026, 9, 24))['items'][0]
        assert item['structurally_ready'] == ready
    item = audit([{**candidate, 'base_code': None, 'properties': {'934': 'Zod Rune'}}], today=date(2026, 9, 24))[
        'items'
    ][0]
    assert item['structurally_ready'] == 0
    assert item['gaps']['base_code'] == 1


def test_missing_rarity_is_a_readiness_gap_even_with_complete_socket_fields():
    item = audit([row(rarity=None)], today=date(2026, 9, 25))['items'][0]
    assert item['structurally_ready'] == 0
    assert item['gaps']['rarity'] == 1


def test_all_items_audit_keeps_base_affixed_and_named_coverage_separate():
    candidates = [
        row(name='A', category='base', rarity='normal', listing_id='a'),
        row(name='B', category='base', rarity='rare', listing_id='b'),
        row(name='C', category='charms', rarity='magic', listing_id='c'),
        row(name='D', category='crafted', rarity=None, listing_id='d'),
        row(
            name='E',
            category='runewords',
            rarity='runeword',
            listing_id='e',
            base_rarity='normal',
            sockets=4,
            socket_contents='filled',
        ),
        row(name='F', category='uniques', rarity='unique', listing_id='f'),
        row(name='G', category='sets', rarity='set', listing_id='g'),
        row(name='Currency', category='runes', rarity=None, listing_id='h'),
    ]
    result = audit(candidates, today=date(2026, 9, 25), all_items=True)
    assert len(result['items']) == 7
    assert result['by_policy']['base']['structurally_ready'] == 1
    assert result['by_policy']['affixed']['scoped_observations'] == 3
    assert result['by_policy']['affixed']['structurally_ready'] == 2
    assert result['by_policy']['named']['structurally_ready'] == 2
    assert result['by_policy']['runeword']['structurally_ready'] == 1
    assert next(r for r in result['items'] if r['name'] == 'D')['gaps']['rarity'] == 1


def test_named_category_does_not_hide_conflicting_explicit_rarity():
    item = audit([row(rarity='rare')], today=date(2026, 9, 25))['items'][0]
    assert item['structurally_ready'] == 0
    assert item['gaps']['rarity'] == 1


def test_runeword_recipe_contents_do_not_require_a_named_item_filler_description():
    word = row(
        name='Spirit',
        category='runewords',
        rarity='runeword',
        base_rarity='normal',
        sockets=4,
        socket_contents='filled',
    )
    result = audit([word], today=date(2026, 9, 25), all_items=True)['items'][0]
    assert result['structurally_ready'] == 1
    assert result['gaps'] == {}
    unknown = audit([{**word, 'base_rarity': None}], today=date(2026, 9, 25), all_items=True)['items'][0]
    assert unknown['gaps']['base_rarity'] == 1
