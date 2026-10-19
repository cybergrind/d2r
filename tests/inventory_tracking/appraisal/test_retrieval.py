from typing import Any

from inventory_tracking.appraisal import retrieval
from tests.inventory_tracking.appraisal.test_text import saved_result


def test_unapproved_type_uses_legacy_and_keeps_triage_as_candidate(monkeypatch):
    from pricing.api import shop_triage
    from pricing.triage import runtime

    observation = saved_result()['result']['extraction']
    monkeypatch.setattr(runtime, 'enabled', lambda _: False)
    monkeypatch.setattr(retrieval, 'triage_enabled', lambda _: False)
    monkeypatch.setattr(retrieval, 'memory_evidence', lambda *_: {'legacy': True})
    result = retrieval.guarded_retrieve(observation, None)
    assert result['legacy'] is True
    assert 'triage' not in result
    assert 'triage_candidate' in result
    assert shop_triage(observation) == {}
    monkeypatch.setattr(runtime, 'enabled', lambda _: True)
    assert 'triage' in retrieval.guarded_retrieve(observation, None)


def test_quest_material_uses_fast_path_without_legacy_assessment(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Legacy appraisal called for enabled material')

    observation = {
        'item': {
            'name': 'Uber Ancient Summon Material Act 1',
            'base_code': 'ua1',
            'rarity': 'normal',
            'ethereal': False,
            'identified': True,
            'sockets': 0,
            'socket_contents': 'empty',
            'affixes': [],
        },
        'source': {'stat_capture_complete': True},
        'decoded_stats': [],
    }
    monkeypatch.setattr(retrieval, 'memory_evidence', forbidden)
    result: dict[str, Any] = retrieval.guarded_retrieve(observation, None)
    assert result['triage']['band']['name'] == "Talic's Anguish"
    assert result['triage']['decision_ist'] is not None


def test_all_rune_and_gem_families_use_fast_triage_including_unseen_drops(monkeypatch):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.socket_materials import TYPES

    def forbidden(*args, **kwargs):
        raise AssertionError('Rune or gem fell back to the detail engine')

    monkeypatch.setattr(retrieval, 'memory_evidence', forbidden)
    monkeypatch.setattr(retrieval, 'retrieve_pinned', forbidden)
    seen = set()
    for base in metadata()['bases'].values():
        if base['type'] not in TYPES | {'rune'}:
            continue
        observation = {
            'item': {
                'name': base['name'],
                'base_code': base['code'],
                'rarity': 'normal',
                'ethereal': False,
                'identified': True,
                'sockets': 0,
                'socket_contents': 'empty',
                'affixes': [],
            },
            'source': {'stat_capture_complete': True},
            'decoded_stats': [],
        }
        assert 'triage' in retrieval.guarded_retrieve(observation, None), base['name']
        seen.add(base['type'])
    assert seen == TYPES | {'rune'}
