from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def item(base, values):
    return replace(facts(base, 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})


def test_lightning_and_fire_claw_roles_require_their_own_skill_combination():
    claw = item('Greater Talons', {'188:48': 2, '107:271': 2, '107:262': 0, '93:0': 20})
    roles = {r['id']: r for r in assess_roles(claw, build()['profiles'])}
    lightning = roles['lightning-sentry-claw-candidate']
    assert lightning['status'] == 'partial'
    assert roles['wake-of-fire-claw-candidate']['status'] == 'failed'
    # Source's ideal +3/+3 and 40 IAS are preferences, not eligibility minimums.
    assert any(p['status'] == 'false' for p in lightning['preferences'])


def test_enchant_prebuff_preserves_mastery_and_skill_identity():
    orb = item('Eldritch Orb', {'188:8': 3, '107:52': 3, '107:61': 3, '105:0': 0})
    role = next(r for r in assess_roles(orb, build()['profiles']) if r['id'] == 'enchant-prebuff-orb-candidate')
    assert role['status'] == 'partial'
    assert role['role'] == 'Enchant prebuff skill combination'
    wrong = item('Eldritch Orb', {'188:8': 3, '107:52': 0, '107:61': 3})
    role = next(r for r in assess_roles(wrong, build()['profiles']) if r['id'] == 'enchant-prebuff-orb-candidate')
    assert role['status'] == 'failed'


def test_absent_skills_are_false_only_with_complete_inventory_and_explicit_rule():
    profiles = build()['profiles']
    claw = item('Greater Claws', {'93:0': 20})
    complete = {r['id']: r for r in assess_roles(claw, profiles)}
    assert complete['lightning-sentry-claw-candidate']['status'] == 'failed'
    partial = {r['id']: r for r in assess_roles(replace(claw, capture_complete=False), profiles)}
    assert partial['lightning-sentry-claw-candidate']['status'] == 'partial'


def test_report_shows_concrete_better_rolls_without_rejecting_lower_candidate():
    from inventory_tracking.appraisal.sections import assessment_lines

    claw = item('Greater Talons', {'188:48': 2, '107:271': 2, '93:0': 20})
    roles = assess_roles(claw, build()['profiles'])
    lines = assessment_lines({'assessment': {'roles': roles}})
    assert any('Better rolls:' in line and '+3 to Lightning Sentry' in line for line in lines)
