import pytest


def test_runtime_comparisons_use_the_pinned_metadata_effects(monkeypatch):
    from pricing.knowledge.assessment.handlers import socket_fillers

    monkeypatch.setattr(
        socket_fillers, 'metadata', lambda: {'comparison_socket_effects': {'helm': {'Test Filler': {'2': 7}}}}
    )
    assert socket_fillers.filler_effects('helm') == {'Test Filler': {2: 7}}
    assert socket_fillers.filler_effects('weapon') == {}


def test_missing_compiled_effects_do_not_recover_unpinned_constants(monkeypatch):
    from pricing.knowledge.assessment.handlers import socket_fillers

    monkeypatch.setattr(socket_fillers, 'metadata', dict)
    assert socket_fillers.filler_effects('helm') == {}


@pytest.mark.parametrize('change', ['variable', 'parameter', 'unknown-function', 'extra-effect', 'empty-effect'])
def test_compiler_rejects_unreviewed_or_nonfixed_effects(change):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.maintenance.comparison_fillers import compile_fillers

    gem = {'name': 'Test Filler', 'helmMod1Code': 'dex', 'helmMod1Min': 10, 'helmMod1Max': 10}
    properties = {'dex': {'func1': 1, 'stat1': 'dexterity'}}
    if change == 'variable':
        gem['helmMod1Max'] = 11
    elif change == 'parameter':
        gem['helmMod1Param'] = 1
    elif change == 'unknown-function':
        properties['dex']['func1'] = 7
    else:
        gem.update(helmMod2Code='unknown', helmMod2Min=1, helmMod2Max=1)
        if change == 'empty-effect':
            properties['unknown'] = {}
    with pytest.raises(ValueError, match='socket'):
        compile_fillers({'test': gem}, properties, metadata()['stats'], {'helm': ['Test Filler']})
