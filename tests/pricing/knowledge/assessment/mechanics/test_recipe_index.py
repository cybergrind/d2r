import pytest

from pricing.knowledge.assessment import base_use
from pricing.knowledge.assessment.adapters.capture import bases_by_code


def test_recipe_index_preserves_all_base_rules_and_mercenary_alternatives():
    rows = base_use.recipe_catalog()
    index = base_use.recipe_index()
    names = {r['name'] for r in rows if r.get('kind') == 'base_rule'}
    assert set(index.by_base) == names
    for name in names:
        assert index.by_base[name] == tuple(r for r in rows if r.get('kind') == 'base_rule' and r['name'] == name)
    types = {b['name']: b['type'] for b in bases_by_code().values()}
    words = {r.get('details', {}).get('runeword') for r in rows}
    for word in words - {None}:
        expected = tuple(
            sorted(
                {
                    r['name']
                    for r in rows
                    if r.get('kind') == 'base_rule'
                    and r.get('details', {}).get('recommended')
                    and r['details'].get('runeword') == word
                    and r['details'].get('context', {}).get('builds_merc')
                    and types.get(r['name']) in ('pole', 'spea')
                }
            )
        )
        assert index.mercenary_alternatives.get(word, ()) == expected
    with pytest.raises(TypeError):
        index.by_base['invented'] = ()


def test_warm_assessment_does_not_iterate_full_recipe_catalog(monkeypatch):
    from pricing.knowledge.assessment.engine import assess
    from tests.pricing.knowledge.assessment.test_base_use import capture

    before = assess(capture('Giant Thresher'), profiles=[])

    def no_scan():
        raise AssertionError('Hot assessment scanned full recipe catalog')

    monkeypatch.setattr(base_use, 'recipe_catalog', no_scan)
    # The old ethereal path imported its own reference to the scanning function.
    from pricing.knowledge.assessment import ethereal

    monkeypatch.setattr(ethereal, 'recipe_catalog', no_scan, raising=False)
    after = assess(capture('Giant Thresher'), profiles=[])
    assert after == before
