"""Player prose cannot inherit a mercenary or another variant's configuration."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import (
    OCCURRENCE_FIELDS,
    compile_source_context_reviews,
)
from tests.pricing.knowledge.assessment.maintenance.test_variant_mercenary_prose import evidence as merc_evidence


def evidence():
    doc, occurrences, profiles, uses = merc_evidence()
    row = doc['rows'][0]
    oid = 'af3130710c7393c25e3ec0f1'
    role = next(p for p in profiles if p['id'] == 'fissure-player-standard-flickering-flame')
    occurrence = next(o for o in occurrences if o['id'] == oid)
    data = json.loads(Path('pricing/data/appraisal-guide-sections.json').read_text())['sources'][
        occurrence['source_id']
    ]
    quote = json.loads(Path('pricing/data/wp-a-builds.json').read_text())['fissure-druid']['variants'][1]['quotes'][0]
    row.update(
        id='fissure-standard-player-flickering-span-19',
        kind='variant_player_narrative',
        occurrence_id=oid,
        expected_occurrence={k: occurrence.get(k) for k in (*OCCURRENCE_FIELDS, 'class')},
        reason='Standard player helmet alternative; ideal base has no numeric staffmod minimum.',
    )
    row['source'].update(locator=row['source']['locator'].rsplit('/', 1)[0] + '/19', expected=data['item_spans'][19])
    row['evidence'].update(locator=row['evidence']['locator'].replace('/25/', '/16/'), quote=quote)
    row['branches'] = [
        {
            'profile_id': role['id'],
            'profile_fingerprint': fingerprint(role),
            'variant': 'Standard',
            'slot': 'Helmet',
            'player_class': 'Druid',
        }
    ]
    doc['rows'] = [row]
    return doc, occurrences, profiles, uses


def test_standard_player_prose_links_exact_variant_without_staffmod_threshold():
    rows = compile_source_context_reviews(*evidence(), Path.cwd())
    assert rows[0]['state'] == 'reviewed'
    assert rows[0]['profile_ids'] == ['fissure-player-standard-flickering-flame']


@pytest.mark.parametrize('change', ['mercenary', 'wrong-variant', 'wrong-section', 'wrong-class', 'no-endorsement'])
def test_player_context_mismatches_are_not_reviewed(change):
    doc, occurrences, profiles, uses = evidence()
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'mercenary':
        p = next(p for p in profiles if p['id'] == 'fissure-merc-ubers-flickering-flame')
        branch.update(profile_id=p['id'], profile_fingerprint=fingerprint(p), variant=p['variant'])
    elif change == 'wrong-variant':
        branch['variant'] = 'Ubers'
    elif change == 'wrong-section':
        row['evidence']['locator'] = row['evidence']['locator'].replace('/16/', '/25/')
    elif change == 'wrong-class':
        branch['player_class'] = 'Sorceress'
    else:
        uses = [u for u in uses if u['profile_id'] != branch['profile_id']]
    with pytest.raises(ValueError, match=r'[Ss]ource-context|variant'):
        compile_source_context_reviews(doc, occurrences, profiles, uses, Path.cwd())


def test_recorded_standard_link_does_not_claim_the_introductory_reference():
    _, occurrences, profiles, uses = evidence()
    doc = json.loads(Path('pricing/knowledge/assessment/rules/source_context_reviews.json').read_text())
    rows = compile_source_context_reviews(doc, occurrences, profiles, uses, Path.cwd())
    linked = {r['occurrence_id']: r['profile_ids'] for r in rows if r['state'] == 'reviewed'}
    assert linked.get('af3130710c7393c25e3ec0f1') == ['fissure-player-standard-flickering-flame']
    # This one exact variant review cannot silently include the broader intro paragraph.
    row = next(r for r in doc['rows'] if r['id'] == 'fissure-standard-player-flickering-span-19')
    assert row['source']['locator'].endswith('/item_spans/19')
