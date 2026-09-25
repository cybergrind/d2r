from dataclasses import replace

from tests.pricing.knowledge.assessment.test_family_contracts import facts


def traveler(mf):
    return replace(
        facts('Battle Boots', 'unique', 'War Traveler'),
        stats={} if mf is None else {'80:0': {'status': 'decoded', 'value': mf}},
    )


def test_named_tier_follows_captured_roll_and_unknown_does_not_get_best_case():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    assert assess_tier(traveler(40))['tier'] == 'low'
    assert assess_tier(traveler(47))['tier'] == 'med'
    assert assess_tier(traveler(50))['tier'] == 'high'
    unknown = assess_tier(traveler(None))
    assert unknown['tier'] is None
    assert unknown['status'] == 'conditional'
    assert set(unknown['possible_tiers']) == {'low', 'med', 'high'}


def test_ethereal_premium_requires_both_flag_and_roll():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    item = replace(
        facts('Ceremonial Javelin', 'unique', "Titan's Revenge"), stats={'17:0': {'status': 'decoded', 'value': 195}}
    )
    assert assess_tier(item)['tier'] == 'med'
    assert assess_tier(replace(item, ethereal=True))['tier'] == 'high'
    assert assess_tier(replace(item, ethereal=None))['tier'] is None


def test_missing_named_policy_is_pending_and_never_implicitly_trash():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    result = assess_tier(facts('Long Sword', 'unique', 'Hellplague'))
    assert result['status'] == 'pending_review'
    assert result['tier'] is None
    assert assess_tier(replace(traveler(50), identified=False))['tier'] is None


def test_report_highlights_resolved_tier_without_creating_numeric_price():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.presentation import Tone
    from pricing.knowledge.assessment.engine import assess

    item = traveler(50)
    extraction = {
        'item': item.to_dict(),
        'decoded_stats': [
            {
                'status': 'decoded',
                'value': 50,
                'memory_stat': {'id': 80, 'layer': 0, 'raw': 50},
                'text': '50% Magic Find',
            }
        ],
        'source': {'stat_capture_complete': True},
    }
    assessment = assess(extraction, profiles=[])
    assert assessment['trade_tier']['tier'] == 'high'
    assert assessment['contract'] is None
    result = {'extraction': extraction, 'assessment': assessment, 'decision': {'price_status': 'unknown'}}
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 1, 'result': result})
    line = next(line for line in document.to_osd() if line.text.startswith('Trade tier:'))
    assert line.tone == Tone.VALUABLE
    assert '2026-09-18' in line.text


def test_named_tier_rejects_conflicting_captured_identity():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    item = replace(traveler(50), provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': 29}}})
    assert assess_tier(item)['tier'] is None
    assert assess_tier(item)['status'] == 'pending_review'
