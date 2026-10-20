import pytest

from inventory_tracking.macros.repair import cost_of


# What tesseract read from the tooltip band of each repair picture kept on 2026-10-17 (runs/alt-d/repair-*.png)
@pytest.mark.parametrize(
    ('text', 'cost'),
    [
        ('= Berar ant cum e: 119636', 119636),
        ('REPAIR ALL couinmenr: 119636', 119636),
        ('Kee REPU Oa cauipmen: 122319', 122319),
        ('ah : REPAIRTALE etl 111469', 111469),
        ('Repair all equipment: 1,234', 1234),
        ("' REPAIR ALL ae 1Q1677", 101677),  # 11:59:59, the font's 0 read as Q (repair-115959.png)
        ('0 REPAIR ALL = 1Q1677', 101677),  # 11:54:16
        ('~~ REPAIR ALL EQUIDIENT: 5@548', 50548),  # 13:24:09, its slashed 0 as @ (repair-132409.png)
    ],
)
def test_the_cost_is_the_last_long_number_of_the_band(text, cost):
    assert cost_of(text) == cost


def test_a_band_with_no_long_number_has_no_cost():
    assert cost_of('REPAIR ALL 12') is None
    assert cost_of('') is None


def test_the_cost_expected_is_the_last_quotes_gold_a_charge_times_the_charges_missing(tmp_path, monkeypatch):
    # 101,677 for 60 charges at 12:04:09 on 2026-10-17; 62,918 for 37 at 12:08:37 was refused against the whole quote
    from inventory_tracking.macros import repair

    monkeypatch.setattr(repair, 'QUOTE_FILE', tmp_path / 'repair-quote.txt')
    monkeypatch.setattr(repair, 'QUOTED', [])
    (tmp_path / 'repair-quote.txt').write_text('101677 60')
    cost = repair.expected(37)
    assert cost is not None
    assert cost == round(101677 / 60 * 37)
    assert abs(62918 - cost) <= repair.QUOTE_DRIFT * cost
    monkeypatch.setattr(repair, 'QUOTED', [])
    (tmp_path / 'repair-quote.txt').write_text('101677')  # the old file: the quote alone
    assert repair.expected(37) == 101677


def test_an_unread_cost_is_paid_only_with_the_carried_gold_far_over_it():
    # 16:25:12 on 2026-10-17: OCR read "Tae ee" from a clear "Repair all equipment: 47449", 548,157 carried
    from inventory_tracking.macros.repair import covered

    assert covered(47_449, 548_157)
    assert not covered(47_449, 120_000)  # under twice the cost and 50,000 more: the stash might pay the rest
    assert not covered(None, 548_157)  # nothing to expect: no repair
    assert not covered(47_449, None)


def test_the_ocr_data_is_kept_out_of_tmp():
    # tmp/ deleted took the English data, and the repair at 01:58:53 on 2026-10-20 read no cost
    from inventory_tracking.macros.repair import TESSDATA

    assert 'tmp' not in TESSDATA.parts
