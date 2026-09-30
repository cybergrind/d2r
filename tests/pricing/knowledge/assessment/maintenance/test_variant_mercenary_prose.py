"""Exact variant provenance may corroborate mercenary prose without changing its role."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import (
    OCCURRENCE_FIELDS,
    compile_source_context_reviews,
)


GUIDE = 'pricing/raw/mr/guides__fissure-druid.html'
CACHE = 'pricing/data/appraisal-guide-sections.json'
SPECS = (
    ('475172513043a06e738abfea', 36, 'fissure-merc-ubers-chains-of-honor'),
    ('567e5103ff315e6feab65d97', 34, 'fissure-merc-ubers-flickering-flame'),
    ('971ced0633872867961e7293', 37, 'fissure-merc-ubers-flickering-flame'),
)


def evidence():
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    cache = json.loads(Path(CACHE).read_text())['sources'][GUIDE]
    pin = {'path': CACHE, 'sha256': hashlib.sha256(Path(CACHE).read_bytes()).hexdigest()}
    prefix = '/sources/' + GUIDE.replace('/', '~1')
    rows = []
    for oid, span, rid in SPECS:
        o = next(o for o in inventory['occurrences'] if o['id'] == oid)
        role = next(p for p in profiles if p['id'] == rid)
        rows.append(
            {
                'id': f'fissure-ubers-merc-span-{span}',
                'kind': 'variant_mercenary_narrative',
                'review_date': '2026-09-28',
                'occurrence_id': oid,
                'expected_occurrence': {k: o.get(k) for k in (*OCCURRENCE_FIELDS, 'class')},
                'reason': 'Exact Ubers mercenary component; class, Might and companion equipment remain required.',
                'source': {**pin, 'locator': prefix + f'/item_spans/{span}', 'expected': cache['item_spans'][span]},
                'evidence': {**pin, 'locator': prefix + '/sections/25/text', 'quote': cache['sections'][25]['text']},
                'branches': [
                    {
                        'profile_id': rid,
                        'profile_fingerprint': fingerprint(role),
                        'variant': 'Ubers',
                        'slot': role['slot'],
                        'player_class': 'Druid',
                        'mercenary_type': 'Act 2 Might',
                    }
                ],
                'remaining_branches': [],
            }
        )
    return {'schema_version': 1, 'rows': rows}, inventory['occurrences'], profiles, uses


def test_exact_ubers_variant_rules_cover_all_three_references():
    result = compile_source_context_reviews(*evidence(), Path.cwd())
    assert {r['occurrence_id'] for r in result if r['state'] == 'reviewed'} == {r[0] for r in SPECS}


@pytest.mark.parametrize('change', ['class', 'mercenary', 'variant', 'slot', 'source', 'different-section'])
def test_variant_link_rejects_incompatible_context_even_with_refreshed_review_fingerprint(change):
    doc, occurrences, profiles, uses = evidence()
    doc['rows'] = doc['rows'][:1]
    row = doc['rows'][0]
    rid = row['branches'][0]['profile_id']
    role = deepcopy(next(p for p in profiles if p['id'] == rid))
    if change == 'class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'mercenary':
        role['depends_on'][0]['when']['value'] = 'Act 2 Holy Freeze'
    elif change == 'variant':
        role['variant'] = row['branches'][0]['variant'] = 'Standard'
    elif change == 'slot':
        role['slot'] = row['branches'][0]['slot'] = 'Helmet'
    elif change == 'source':
        role['source']['locator'] = '/fissure-druid/variants/1'
    else:
        row['source']['locator'] = row['source']['locator'].replace('/36', '/23')
    row['branches'][0]['profile_fingerprint'] = fingerprint(role)
    profiles = [role if p['id'] == rid else p for p in profiles]
    for u in uses:
        if u['profile_id'] == rid:
            u.update({k: role[k] for k in ('source', 'variant')})
            u['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'[Ss]ource-context|variant'):
        compile_source_context_reviews(doc, occurrences, profiles, uses, Path.cwd())


def test_repository_links_retain_the_reviewed_ubers_bearer():
    _, occurrences, profiles, uses = evidence()
    doc = json.loads(Path('pricing/knowledge/assessment/rules/source_context_reviews.json').read_text())
    rows = compile_source_context_reviews(doc, occurrences, profiles, uses, Path.cwd())
    actual = {r['occurrence_id']: r['profile_ids'] for r in rows if r['state'] == 'reviewed'}
    for oid, _, role in SPECS:
        assert actual.get(oid) == [role]
