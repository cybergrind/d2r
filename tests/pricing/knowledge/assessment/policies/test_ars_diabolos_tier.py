from dataclasses import replace

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def grimoire():
    return replace(
        facts('Blasphemous Grimoire', 'unique', "Ars Al'Diabolos"),
        stats={
            key: {'status': 'decoded', 'value': value}
            for key, value in [('16:0', 198), ('329:0', 18), ('138:0', 8), ('39:0', 29), ('107:401', 3)]
        },
    )


def test_ars_diabolos_has_reviewed_high_priority_without_invented_numeric_price():
    result = assess_tier(grimoire())
    assert result['status'] == 'reviewed'
    assert result['tier'] == 'high'
    assert result['source']['date'] == '2026-09-18'
    assert 'estimate_ist' not in result


def test_ars_diabolos_missing_skill_or_unsupported_roll_stays_unresolved():
    item = grimoire()
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != '107:401'})
    assert assess_tier(missing)['status'] == 'conditional'
    for changed in [replace(item, ethereal=True), replace(item, socket_contents='filled')]:
        assert assess_tier(changed)['tier'] is None
    for key, value in [('16:0', 201), ('329:0', 26), ('138:0', 11), ('39:0', 31), ('107:401', 6)]:
        bad = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value}})
        assert assess_tier(bad)['tier'] is None
