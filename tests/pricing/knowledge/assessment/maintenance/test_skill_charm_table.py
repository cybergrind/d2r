"""Skill-charm table links require native affixes and the actual planner item."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]


def read(path):
    return json.loads((ROOT / path).read_bytes())


def pin(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


@pytest.fixture(scope='module')
def evidence():
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    reviews = []
    for suffix, span, suffixes in [
        ('vita', 149, [338, 339]),
        ('balance', 150, [265]),
        ('inertia', 151, [399]),
        ('plain', 152, []),
    ]:
        role = next(p for p in profiles if p['id'] == 'fissure-elemental-grand-charm-' + suffix)
        occurrence = next(
            o
            for o in occurrences
            if o['source_id'] == 'pricing/raw/mr/guides__fissure-druid.html'
            and o['source_locator'] == f'/item-spans/{span}'
        )
        use = next(u for u in uses if u['profile_id'] == role['id'])
        reviews.append(
            {
                'occurrence_id': occurrence['id'],
                'occurrence_fingerprint': fingerprint(occurrence),
                'profile_id': role['id'],
                'profile_fingerprint': fingerprint(role),
                'use_fingerprint': fingerprint(use),
                'review_date': '2026-10-01',
                'reason': 'Exact Elemental skiller and suffix in the linked Fissure planner.',
                'pattern_kind': 'native_skill_grand_charm',
                'pattern_label': occurrence['original_label'],
                'guide': pin('pricing/raw/mr/guides__fissure-druid.html'),
                'cache': pin('pricing/data/appraisal-guide-sections.json'),
                'planner': pin('pricing/raw/mr/planners/vf0106vk.json'),
                'prefixes': pin('third-parties/d2data/json/magicprefix.json'),
                'prefix_id': 492,
                'suffixes': pin('third-parties/d2data/json/magicsuffix.json'),
                'suffix_ids': suffixes,
            }
        )
    return reviews, occurrences, profiles, uses


def test_exact_native_skill_charm_tables(evidence):
    reviews, occurrences, profiles, uses = evidence
    result = compile_table_equivalence({'schema_version': 1, 'rows': reviews}, occurrences, profiles, uses, ROOT)
    assert {r['profile_id'] for r in result if r['state'] == 'reviewed'} == {r['profile_id'] for r in reviews}


@pytest.mark.parametrize(
    'mutation', ['wrong-tree', 'wrong-suffix', 'unattainable-tier', 'missing-suffix', 'wrong-planner']
)
def test_skill_charm_table_rejects_incompatible_native_witnesses(evidence, mutation):
    original, occurrences, profiles, uses = evidence
    review = deepcopy(original[0])
    if mutation == 'wrong-tree':
        review['prefix_id'] = 490
    elif mutation == 'wrong-suffix':
        review['suffix_ids'] = [399]
    elif mutation == 'unattainable-tier':
        review['suffix_ids'].append(340)
    elif mutation == 'missing-suffix':
        review['suffix_ids'] = []
    else:
        review['planner'] = pin('pricing/raw/mr/planners/db0106mf.json')
    with pytest.raises(ValueError, match=r'[Ss]kill charm'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)


@pytest.mark.parametrize('mutation', ['ethereal', 'socket', 'rare', 'extra-affix', 'out-of-range', 'totals'])
def test_skill_charm_table_rejects_inconsistent_planner_payload(evidence, monkeypatch, mutation):
    from pricing.knowledge.assessment.maintenance import skill_charm_table

    reviews, occurrences, profiles, uses = evidence
    planner = skill_charm_table.decode_planner(read('pricing/raw/mr/planners/vf0106vk.json'))
    item = planner['items']['23']
    if mutation == 'ethereal':
        item['ethereal'] = True
    elif mutation == 'socket':
        item['sockets'] = 1
    elif mutation == 'rare':
        item['quality'] = 5
    elif mutation == 'extra-affix':
        item['mods']['ms399'] = [7]
    elif mutation == 'out-of-range':
        item['mods']['ms339'] = [46]
        item['stats']['maxhp'] = 46
    else:
        item['stats']['maxhp'] = 44
    monkeypatch.setattr(skill_charm_table, 'decode_planner', lambda raw: planner)
    with pytest.raises(ValueError, match='Planner'):
        compile_table_equivalence({'schema_version': 1, 'rows': [reviews[0]]}, occurrences, profiles, uses, ROOT)
