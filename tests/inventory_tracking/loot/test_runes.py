"""Rune class IDs from d2data misc.json (class ID = lineNumber + 523, anchored on confirmed IDs)."""

import pytest

from inventory_tracking.loot.runes import RUNES, is_valuable_rune, rune_name


def test_rune_ids_are_the_contiguous_el_to_zod_block():
    assert (rune_name(625), rune_name(645), rune_name(657)) == ('El Rune', 'Pul Rune', 'Zod Rune')
    assert sorted(RUNES) == list(range(625, 658))


@pytest.mark.parametrize(('class_id', 'expected'), [(644, False), (645, True), (657, True), (606, False), (534, False)])
def test_valuable_means_the_configured_rune_or_higher(class_id, expected):
    assert is_valuable_rune(class_id, minimum='r21') is expected  # r21 = Pul, the ladder's first rune


def test_every_rune_class_id_matches_the_item_decoder():
    # The decoder's bases come from the game's classid column and name real inventory items; the
    # old "misc.json lineNumber + 523" rule was one too high for runes (user saw Ist named Mal).
    from inventory_tracking.items.metadata import item_base
    from inventory_tracking.loot.runes import RUNES

    assert len(RUNES) == 33
    for class_id, rune in RUNES.items():
        assert (item_base(class_id)['code'], item_base(class_id)['name']) == (rune['code'], rune['name'])
