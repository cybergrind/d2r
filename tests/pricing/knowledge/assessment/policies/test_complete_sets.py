import json

from pricing.knowledge.assessment.policies.complete_sets import ROOT, assess_complete_set
from pricing.knowledge.definition_store import catalog


def test_all_native_sets_have_independent_tiers_and_exact_membership():
    native = json.loads((ROOT / 'third-parties/d2data/json/sets.json').read_bytes())
    for key in native:
        result = assess_complete_set(key)
        assert result['tier'] in {'high', 'med', 'low', 'trash'}, key
        expected = {
            d['name']
            for (quality, _), d in catalog().named.items()
            if quality == 'set' and d['game_definition']['set'] == key
        }
        assert set(result['pieces']) == expected
        assert result['ownership'] == 'not_evaluated'


def test_full_set_does_not_inherit_best_component_or_imply_owned():
    assert assess_complete_set("Tal Rasha's Wrappings")['tier'] == 'med'
    assert assess_complete_set("Sigon's Complete Steel")['leveling']['tier'] == 'high'
    assert assess_complete_set('unknown set')['tier'] is None


def test_single_piece_report_labels_full_set_tier_separately():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.presentation import Tone

    document = ItemAssessment.from_record(
        {
            'state': 'complete',
            'request_id': 1,
            'result': {
                'extraction': {
                    'item': {'name': "Tal Rasha's Horadric Crest", 'rarity': 'set', 'set_name': "Tal Rasha's Wrappings"}
                },
                'assessment': {
                    'trade_tier': {
                        'status': 'reviewed',
                        'tier': 'low',
                        'set_context': assess_complete_set("Tal Rasha's Wrappings"),
                    }
                },
                'decision': {'price_status': 'unknown'},
            },
        }
    )
    lines = document.to_osd()
    assert next(line for line in lines if line.text.startswith('Set:')).tone == Tone.TIER_MED
    assert next(line for line in lines if line.text.startswith('Trade tier:')).tone == Tone.TIER_LOW
    assert any('full-set trade tier: mid' in line.text for line in lines)
