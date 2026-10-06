"""Expensive uniques by base item: loot/data/uniques.json joins the dated ask table with the item decoder."""

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.uniques import BASES, unique_drop


BY_CODE = {base['code']: int(class_id) for class_id, base in metadata()['bases'].items()}


def unique_id(name):
    [table_id] = [int(key) for key, row in metadata()['identities']['unique'].items() if row['name'] == name]
    return table_id


def test_a_base_with_one_unique_names_it():
    assert unique_drop(BY_CODE['7gw'], minimum=4.0) == "Death's Web"
    assert unique_drop(BY_CODE['uap'], minimum=2.0) == 'Harlequin Crest'


def test_a_base_whose_uniques_all_ask_less_is_not_marked():
    assert unique_drop(BY_CODE['uap'], minimum=4.0) is None  # Harlequin Crest: 2.58 Ist asks, 2026-09-18
    assert unique_drop(BY_CODE['hax'], minimum=0.0) is None  # The Gnasher: no asks pulled


def test_a_base_with_several_uniques_names_the_dearest_as_a_guess():
    assert unique_drop(BY_CODE['rin'], minimum=4.0) == 'Unique Ring (Sling?)'
    assert unique_drop(BY_CODE['amu'], minimum=4.0) == "Unique Amulet (Mara's Kaleidoscope?)"


def test_item_data_naming_a_unique_of_this_base_is_used_as_the_name():
    # Whether the ground item's +0x34 is filled before identification is unconfirmed on this build:
    # a value that names a unique of another base is ignored, and it never hides a mark.
    assert unique_drop(BY_CODE['rin'], minimum=4.0, table_id=unique_id('Nagelring')) == 'Nagelring'
    assert unique_drop(BY_CODE['rin'], minimum=4.0, table_id=unique_id("Death's Web")) == 'Unique Ring (Sling?)'


def test_an_identified_unique_is_judged_by_its_own_asks():
    nagelring, jordan = unique_id('Nagelring'), unique_id('The Stone of Jordan')
    assert unique_drop(BY_CODE['rin'], minimum=4.0, table_id=nagelring, identified=True) is None
    assert unique_drop(BY_CODE['rin'], minimum=2.0, table_id=jordan, identified=True) == 'The Stone of Jordan'


def test_every_listed_base_is_the_decoders_base_and_holds_a_priced_unique():
    assert len(BASES) > 30
    for class_id, base in BASES.items():
        assert metadata()['bases'][str(class_id)]['code'] == base['code']
        assert any(unique['high'] is not None for unique in base['uniques'])


def test_the_default_threshold_marks_harlequin_crest_and_the_stone_of_jordan():
    from inventory_tracking.config import APPRAISAL

    minimum = APPRAISAL.unique_minimum  # user, 2026-10-06: both ask 2.58 Ist (2026-09-18)
    assert unique_drop(BY_CODE['uap'], minimum=minimum) == 'Harlequin Crest'
    jordan = unique_id('The Stone of Jordan')
    assert unique_drop(BY_CODE['rin'], minimum=minimum, table_id=jordan, identified=True) == 'The Stone of Jordan'
