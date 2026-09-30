"""Opalvein's source review must name its real proc and conditional fire modifier."""

import json

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.policies.sources import resolve_pointer


ROLE = 'fire-warlock-guide-opalvein-caster-utility-alternative'


def test_opalvein_review_corroborates_the_native_proc_and_random_group():
    profile = next(row for row in build()['profiles'] if row['id'] == ROLE)
    refs = {row['path']: row for row in profile['source']['corroborating']}
    native = json.loads((ROOT / 'third-parties/d2data/json/uniqueitems.json').read_text())['416']
    skills = 'third-parties/d2data/json/skills.json'
    assert resolve_pointer(json.loads((ROOT / skills).read_text()), refs[skills]['locator'])['skill'] == native['par1']
    groups = 'third-parties/d2data/json/propertygroups.json'
    group = resolve_pointer(json.loads((ROOT / groups).read_text()), refs[groups]['locator'])
    assert group['code'] == native['prop2']
    assert group['PickMode'] == 1
    assert (group['Prop3'], group['ModMin3'], group['ModMax3']) == ('extra-fire', 3, 5)


def test_opalvein_review_prioritizes_only_the_fire_random_modifier():
    compiled = build()
    review = next(row for row in compiled['stat_evaluation']['reviews'] if row['role_id'] == ROLE)
    priorities = {row['key']: row for row in review['priorities']}
    assert priorities['329:0']['desirability'] == 'desirable'
    assert priorities['329:0']['activation'] == {
        'op': 'stat_at_least',
        'key': '329:0',
        'value': 1,
        'absent_is_zero': True,
    }
    assert not {'357:0', '17:0', '18:0', '330:0', '331:0', '332:0', '195:25487'} & priorities.keys()
