"""The recommended Holy Bolt weapon proves its actual rare-jewel affixes."""

from copy import deepcopy

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate


PID = 'fist-of-the-heavens-paladin-4-hand-support-jewel'


def current_records():
    review = deepcopy(
        next(
            r
            for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
            if r['profile_id'] == 'fist-of-the-heavens-paladin-4-vipermagi-ber'
        )
    )
    role = next(p for p in read('pricing/data/appraisal-build-profiles.json')['profiles'] if p['id'] == PID)
    occurrence = next(
        o
        for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences']
        if o.get('source_id') == 'pricing/data/wp-a-builds.json'
        and o.get('source_locator') == '/fist-of-the-heavens-paladin/variants/4/player/Weapon/0'
    )
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == PID
    )
    planner = decode_planner(read('pricing/raw/mr/planners/s10106pr.json'))
    review.update(
        profile_id=PID,
        profile_fingerprint=fingerprint(role),
        canonical_name='Hand of Blessed Light',
        occurrence_id=occurrence['id'],
        occurrence_fingerprint=fingerprint(occurrence),
        use_fingerprint=fingerprint(use),
        required_predicates=role['must']['all'],
        required_conditions=role['conditions'],
        reason=(
            'Explicit Holy Bolt recommendation; exact ethereal player weapon1 and rare child55. '
            'Native minimum affix combination is useful without perfect rolls; '
            'no parent-total, spell-damage or full-loadout inference.'
        ),
    )
    evidence = review['planner_endorsement']
    evidence.update(
        coverage='player_rare_jewel_component',
        slot='rarm',
        item_id='1',
        expected_item=planner['items']['1'],
        jewel={
            'item_id': '55',
            'expected_item': planner['items']['55'],
            'affix_definitions': {
                'mp': pin('third-parties/d2data/json/magicprefix.json'),
                'ms': pin('third-parties/d2data/json/magicsuffix.json'),
            },
            'stat_definitions': pin('third-parties/d2data/json/itemstatcost.json'),
        },
    )
    evidence.pop('ethereal_scope')
    evidence.pop('rune_definitions')
    return review, occurrence, role, use


def test_explicit_holy_bolt_weapon_and_actual_rare_child_validate():
    assert validate(current_records())['state'] == 'reviewed'


def test_registered_hand_source_pins_actual_child_and_affixes():
    records = current_records()
    matching = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == records[1]['id']
    ]
    assert len(matching) == 1
    assert matching[0]['profile_id'] == PID
    assert matching[0]['planner_endorsement']['coverage'] == 'player_rare_jewel_component'
    assert matching[0]['planner_endorsement']['jewel']['item_id'] == '55'
    assert validate((matching[0], *records[1:]))['state'] == 'reviewed'


def test_completion_accepts_corroborating_review_without_double_counting():
    from pricing.knowledge.assessment.maintenance.completion import compile_completion

    review, occurrence, _role, _use = current_records()
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    inventory = read('pricing/data/appraisal-guide-inventory.json')
    inventory['occurrences'] = [occurrence]
    for identity in inventory['identities']:
        identity['occurrence_ids'] = [oid for oid in identity['occurrence_ids'] if oid == occurrence['id']]
    inventory['embedded_item_links'] = []
    inventory['planner_sources'] = []
    result = compile_completion(
        {'rows': []},
        inventory,
        {'complete': True},
        profiles=profiles,
        uses=uses,
        table_reviews={'schema_version': 1, 'rows': [review]},
    )
    assert result['counts']['reviewed_occurrences'] == 1
    assert 'occurrence:' + occurrence['id'] not in {r['id'] for r in result['queue']}
    assert not result['complete']
