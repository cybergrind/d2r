"""A gemmed table entry needs its own endorsed configuration and wearer proof."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import (
    OCCURRENCE_FIELDS,
    compile_source_context_reviews,
)


ROOT = Path(__file__).resolve().parents[5]


def mask_review():
    def read(path):
        return json.loads((ROOT / path).read_bytes())

    rules = 'pricing/knowledge/assessment/rules/'
    reviews = read(rules + 'source_context_reviews.json')
    row = deepcopy(next(r for r in reviews['rows'] if r['id'] == 'abyss-named-merc-table-span-110'))
    inventory = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    occurrence = next(
        o
        for o in inventory
        if o['source_id'] == row['expected_occurrence']['source_id']
        and o['source_locator'] == '/item-spans/112'
        and o['kind'] == 'demand'
    )
    role = next(
        r
        for r in read('pricing/data/appraisal-build-profiles.json')['profiles']
        if r['id'] == 'abyss-warlock-merc-resistance-mask'
    )
    uses = [u for u in read(rules + 'guide_use_reviews.json')['uses'] if u['profile_id'] == role['id']]
    guide = read('pricing/data/appraisal-guide-sections.json')['sources'][occurrence['source_id']]
    row.update(
        id='abyss-pattern-merc-table-span-112',
        kind='mercenary_table_pattern_correction',
        occurrence_id=occurrence['id'],
        expected_occurrence={k: occurrence.get(k) for k in (*OCCURRENCE_FIELDS, 'class')},
    )
    row['source']['locator'] = row['source']['locator'].rsplit('/', 1)[0] + '/112'
    row['source']['expected'] = guide['item_spans'][112]
    row['branches'][0].update(
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        variant=role['variant'],
        slot=role['slot'],
        qualities=role['qualities'],
        pattern_label='Gemmed Mask',
    )
    return row, occurrence, role, uses


def test_exact_gemmed_mask_configuration_has_reviewed_mercenary_source():
    row, occurrence, role, uses = mask_review()
    original = deepcopy(occurrence)
    result = compile_source_context_reviews({'schema_version': 1, 'rows': [row]}, [occurrence], [role], uses, ROOT)
    assert result[0]['state'] == 'reviewed'
    assert occurrence == original


@pytest.mark.parametrize('change', ['label', 'quality', 'wearer', 'named', 'class', 'mercenary', 'endorsement'])
def test_pattern_cannot_borrow_unrelated_identity_or_wearer(change):
    row, occurrence, role, uses = mask_review()
    branch = row['branches'][0]
    if change == 'label':
        branch['pattern_label'] = 'Other helmet'
    elif change == 'quality':
        branch['qualities'] = ['rare']
    elif change == 'wearer':
        row['wearer_quote'] = 'Equip your player with Gemmed Mask.'
    elif change == 'named':
        role['names'] = ['Undead Crown']
    elif change in ('class', 'mercenary'):
        field = 'player_class' if change == 'class' else 'mercenary_type'
        next(p for p in role['must']['all'] if p.get('field') == field)['value'] = 'Other'
    else:
        uses[0]['pattern_label'] = 'Other helmet'
    branch['profile_fingerprint'] = uses[0]['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'source-context|mercenary table|guide-use'):
        compile_source_context_reviews({'schema_version': 1, 'rows': [row]}, [occurrence], [role], uses, ROOT)
