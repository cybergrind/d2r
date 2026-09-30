from dataclasses import replace

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.presentation import Tone
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('ethereal', 'ed', 'expected'), [(False, 187, 'low'), (True, 199, 'low'), (True, 200, 'high'), (None, None, 'low')]
)
def test_guardian_baseline_survives_failed_or_unknown_premium(ethereal, ed, expected):
    item = replace(facts('Templar Coat', 'unique', 'Guardian Angel'), ethereal=ethereal)
    decoded = (
        []
        if ed is None
        else [
            {
                'status': 'decoded',
                'value': ed,
                'memory_stat': {'id': 16, 'layer': 0, 'raw': ed},
                'text': f'{ed}% Enhanced Defense',
            }
        ]
    )
    extraction = {'item': item.to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}
    result = assess(extraction, profiles=[])
    assert result['trade_tier']['tier'] == expected
    assert result['trade_tier']['baseline']['tier'] == 'low'
    document = ItemAssessment.from_record(
        {
            'state': 'complete',
            'request_id': 1,
            'result': {'extraction': extraction, 'assessment': result, 'decision': {'price_status': 'unknown'}},
        }
    )
    line = next(line for line in document.to_osd() if line.text.startswith('Trade tier:'))
    assert line.tone == (Tone.TIER_HIGH if expected == 'high' else Tone.TIER_LOW)


def test_unknown_roll_keeps_baseline_without_claiming_premium():
    from pricing.knowledge.assessment.policies.named_baselines import assess_tier

    item = facts('Battle Boots', 'unique', 'War Traveler')
    tier = assess_tier(item)
    assert tier['tier'] == 'low'
    assert tier['variant']['status'] == 'conditional'
    assert tier['variant']['tier'] is None


def test_identity_conflict_cannot_receive_baseline():
    from pricing.knowledge.assessment.policies.named_baselines import assess_tier

    item = facts('Templar Coat', 'unique', 'Guardian Angel')
    assert assess_tier(replace(item, identified=False))['tier'] is None
    assert assess_tier(replace(item, base_code=facts('Cap').base_code))['tier'] is None


def test_every_eligible_native_identity_renders_a_baseline_with_unknown_premium_facts():
    import json

    from inventory_tracking.appraisal.sections import tier_lines
    from pricing.knowledge.assessment.policies.named_baselines import RULES, assess_tier, baselines
    from pricing.knowledge.definition_store import catalog

    rows = baselines(RULES.read_bytes())
    reviews = json.loads((RULES.parent / 'named_tier_reviews.json').read_bytes())
    excluded = {(r['quality'], r['name']) for r in reviews['non_trade_definitions']}
    assert rows.keys() | excluded == catalog().named.keys()
    assert not rows.keys() & excluded
    failures = []
    for identity, variants in catalog().named_variants.items():
        if identity in excluded:
            continue
        for definition in variants:
            item = replace(
                facts('Cap'),
                name=identity[1],
                rarity=identity[0],
                base_code=definition['base_codes'][0],
                provenance={'capture': {'item_identity': {'table': identity[0], 'table_id': definition['table_id']}}},
                capture_complete=False,
                ethereal=None,
                sockets=None,
                socket_contents='unknown',
            )
            tier = assess_tier(item)
            if tier.get('tier') is None or not tier_lines({'assessment': {'trade_tier': tier}}):
                failures.append((identity, definition['table_id'], tier))
    assert failures == []
