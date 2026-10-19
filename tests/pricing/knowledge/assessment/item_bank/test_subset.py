from tests.pricing.knowledge.assessment.item_bank.cases import CASES
from tests.pricing.knowledge.assessment.item_bank.subset import default_ids, full_bank, owners


def test_default_subset_is_small_and_covers_every_module_rarity_and_scenario():
    ids = default_ids()
    chosen = [case for case in CASES if case.id in ids]
    assert 1000 <= len(ids) <= 2000
    assert len(chosen) == len(ids)
    module = owners()
    assert {module[case.id] for case in chosen} == set(module.values())
    assert {(c.item.rarity, c.scenario) for c in chosen} == {(c.item.rarity, c.scenario) for c in CASES}
    for facet in (lambda c: c.scenario, lambda c: c.item.rarity):
        assert {(module[c.id], facet(c)) for c in chosen} == {(module[c.id], facet(c)) for c in CASES}


def test_default_subset_is_deterministic():
    assert default_ids() == default_ids.__wrapped__()


def test_full_bank_is_opt_in(monkeypatch):
    monkeypatch.delenv('D2R_ITEM_BANK', raising=False)
    assert not full_bank()
    monkeypatch.setenv('D2R_ITEM_BANK', 'full')
    assert full_bank()
