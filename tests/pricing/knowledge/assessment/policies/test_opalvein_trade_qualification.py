from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(choice=329, roll=3):
    return Item(
        'Ring',
        'unique',
        'Opalvein',
        ((choice, 0, roll), (39, 0, 6), (41, 0, 6), (43, 0, 6), (45, 0, 6), (86, 0, 1), (138, 0, 1)),
        complete=True,
    )


@pytest.mark.parametrize('choice', [329, 331, 330])
@pytest.mark.parametrize('roll', [3, 5])
def test_only_supported_elemental_variants_claim_ordinary_trade(choice, roll):
    assert assess_trade_qualification(normalize(item(choice, roll).capture()))['status'] == (
        'unresolved' if choice == 330 else 'candidate'
    )


@pytest.mark.parametrize('choice', [357, 332])
def test_other_random_variants_cannot_borrow_elemental_demand(choice):
    assert assess_trade_qualification(normalize(item(choice).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'change', ['incomplete', 'second-choice', 'missing-choice', 'unequal-resists', 'missing-recovery', 'invalid-choice']
)
def test_random_choice_and_all_material_rolls_must_be_verified(change):
    specimen = item()
    if change == 'incomplete':
        specimen = replace(specimen, complete=False)
    elif change == 'second-choice':
        specimen = replace(specimen, raw_stats=(*specimen.raw_stats, (357, 0, 3)))
    elif change == 'missing-choice':
        specimen = replace(specimen, raw_stats=specimen.raw_stats[1:])
    elif change == 'unequal-resists':
        specimen = replace(specimen, raw_stats=tuple((s, p, 7 if s == 39 else v) for s, p, v in specimen.raw_stats))
    elif change == 'missing-recovery':
        specimen = replace(specimen, raw_stats=tuple(r for r in specimen.raw_stats if r[0] != 138))
    else:
        specimen = item(roll=6)
    assert assess_trade_qualification(normalize(specimen.capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('change', ['mixed-choice', 'unreviewed-mode', 'thin-cohort'])
def test_market_choice_identity_and_each_cohort_are_enforced(change):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == 'Opalvein')['trade_qualification']
    if change == 'mixed-choice':
        review['market_evidence'][0]['properties']['510'] = 30
    elif change == 'unreviewed-mode':
        review['property_choice'] = 'any-random-roll'
    else:
        rows = [r for r in review['market_evidence'] if '750' in r['properties']]
        for row in rows:
            row['seller_id'] = rows[0]['seller_id']
    with pytest.raises(
        ValueError, match=r'Unverified trade evidence|Unsupported trade property|Insufficient independent'
    ):
        _policies(json.dumps(document).encode())


@pytest.mark.parametrize('choice', [357, 332])
def test_valid_other_choices_keep_the_existing_identity_tier_without_trade_qualification(choice):
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    facts = normalize(item(choice).capture())
    assert assess_tier(facts)['tier'] == 'high'
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


def test_valid_physical_choice_keeps_identity_tier_without_elemental_qualification():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    base = item()
    physical = replace(base, raw_stats=((17, 0, 30), (18, 0, 30), *base.raw_stats[1:]))
    facts = normalize(physical.capture())
    assert assess_tier(facts)['tier'] == 'high'
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


def test_partial_capture_keeps_existing_tier_but_cannot_claim_verified_random_variant():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    base = item()
    facts = normalize(replace(base, complete=False, raw_stats=base.raw_stats[1:]).capture())
    assert assess_tier(facts)['tier'] == 'high'
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


def test_reviewed_choice_subset_cannot_borrow_an_unreviewed_element():
    from pricing.knowledge.assessment.policies.trade_choices import valid_reviewed_choice

    review = {'property_choice': 'opalvein_elemental', 'choice_keys': ['329:0', '331:0']}
    assert valid_reviewed_choice(review, normalize(item(329).capture()))
    assert not valid_reviewed_choice(review, normalize(item(330).capture()))
