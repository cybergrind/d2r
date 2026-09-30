from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def with_stats(item, **values):
    return replace(item, stats={key: {'status': 'decoded', 'value': value} for key, value in values.items()})


@pytest.mark.parametrize(
    ('base', 'name'),
    [
        ('Long Sword', 'Hellplague'),
        ('Jewel', 'Rainbow Facet'),
        ('Vampirebone Gloves', "Dracul's Grasp"),
    ],
)
def test_unknown_capture_is_not_assigned_best_roll_tier(base, name):
    assert assess_tier(replace(facts(base, 'unique', name), identified=False))['tier'] is None


@pytest.mark.parametrize(
    ('base', 'name'),
    [
        ('Buckler', 'Pelta Lunata'),
        ('Short Staff', 'Bane Ash'),
        ('Defender', 'Visceratuant'),
        ('Long Sword', 'Hellplague'),
        ('Rune Staff', 'Skull Collector'),
    ],
)
def test_current_utility_is_retained_despite_historical_trash_label(base, name):
    assert assess_tier(facts(base, 'unique', name))['tier'] == 'low'


def test_ethereal_death_cleaver_has_separate_premium_branch():
    item = facts('Berserker Axe', 'unique', 'Death Cleaver')
    assert assess_tier(item)['tier'] == 'low'
    assert assess_tier(replace(item, ethereal=True))['tier'] == 'high'
    assert assess_tier(replace(item, ethereal=None))['tier'] is None


def test_arkaine_skill_roll_gates_useful_variant():
    item = facts('Balrog Skin', 'unique', "Arkaine's Valor")
    assert assess_tier(with_stats(item, **{'127:0': 1}))['tier'] == 'low'
    assert assess_tier(with_stats(item, **{'127:0': 2}))['tier'] == 'med'
    assert assess_tier(item)['tier'] is None


def test_rainbow_facet_does_not_mix_elements_for_perfect_roll():
    from pricing.knowledge.definition_store import catalog

    fire = next(
        v
        for v in catalog().named_variants['unique', 'Rainbow Facet']
        if any(r['property'] == 'extra-fire' for r in v['roll_ranges'].values())
    )
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': fire['table_id']}}},
    )
    # Fire skill damage / enemy fire resistance; native IDs verified in metadata.
    assert assess_tier(with_stats(item, **{'329:0': 3, '333:0': 3}))['tier'] == 'low'
    assert assess_tier(with_stats(item, **{'329:0': 5, '333:0': 5}))['tier'] == 'high'
    assert assess_tier(with_stats(item, **{'329:0': 5, '334:0': 5}))['tier'] is None


def test_qualitative_tier_report_does_not_claim_cached_market_asks():
    from inventory_tracking.appraisal.sections import tier_lines

    tier = assess_tier(facts('Long Sword', 'unique', 'Hellplague'))
    lines = tier_lines({'assessment': {'trade_tier': tier}})
    assert lines == ['Trade tier: low']
