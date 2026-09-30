"""Source-use closure does not close independent item, variant or market work."""

import copy
import hashlib
import json
import shutil

import pytest

from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.reward_mentions import FIELDS
from pricing.knowledge.assessment.maintenance.utility_source_reviews import compile_utility_source_reviews
from pricing.knowledge.assessment.policies.consumables import SOURCE, SOURCE_SHA256


def example(root):
    gid = 'pricing/raw/mr/guides__zeal-paladin.html'
    prefix = '/sources/pricing~1raw~1mr~1guides__zeal-paladin.html'
    span = {'label': 'Thawing Potion', 'side': 'merc', 'slot': 'unspecified', 'item_id': '', 'profile_id': None}
    quote = 'The Mercenary also gains bonus Resistances from Thawing Potions and Antidote Potions.'
    cache = root / 'pricing/data/appraisal-guide-sections.json'
    cache.parent.mkdir(parents=True)
    html = (
        '<h3>Mercenary</h3><p>'
        + quote.replace('Thawing Potion', '<span class="d2planner-item">Thawing Potion</span>')
        + '</p>'
    )
    raw = root / gid
    raw.parent.mkdir(parents=True)
    raw.write_text(html)
    cache.write_text(json.dumps({'sources': {gid: section_inventory(html)}}))
    native = root / 'third-parties/d2data/json/misc.json'
    native.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE, native)
    occurrence = dict(
        id='potion-use',
        name='Thawing Potion',
        original_label='Thawing Potion',
        kind='demand',
        category='misc',
        build='zeal-paladin',
        variant='Guide mention',
        side='merc',
        slot='unspecified',
        source_id=gid,
        source_locator='/item-spans/0',
        identity_id='a',
        identity_status='resolved',
        **{'class': 'Paladin'},
    )
    ref = {'path': str(cache.relative_to(root)), 'sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}
    row = {
        'id': 'merc-thawing',
        'occurrence_id': 'potion-use',
        'review_date': '2026-09-27',
        'reason': 'Temporary cold resistance consumable for the mercenary; no equipped-item or price inference.',
        'expected_occurrence': {k: occurrence.get(k) for k in FIELDS},
        'source': {**ref, 'locator': prefix + '/item_spans/0', 'expected': span},
        'evidence': {**ref, 'locator': prefix + '/sections/1/text', 'quote': quote},
        'policy': {
            'id': 'consumable:wms',
            'recipient': 'mercenary',
            'native_source': {
                'path': 'third-parties/d2data/json/misc.json',
                'sha256': SOURCE_SHA256,
                'locator': '/wms',
            },
        },
        'item_bank_target': 'consumable:wms',
    }
    return {'schema_version': 1, 'rows': [row]}, [occurrence]


def test_mercenary_consumable_use_links_to_exact_native_policy(tmp_path):
    doc, occurrences = example(tmp_path)
    before = copy.deepcopy(occurrences)
    result = compile_utility_source_reviews(doc, occurrences, tmp_path)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['policy_id'] == 'consumable:wms'
    assert result[0]['occurrence_id'] == 'potion-use'
    assert occurrences == before


@pytest.mark.parametrize(
    'change',
    [
        'unknown-code',
        'wrong-identity',
        'wrong-recipient',
        'stale-native',
        'stale-guide',
        'changed-occurrence',
        'wrong-slot',
        'wrong-bank',
        'no-merc-prose',
        'foreign-guide',
        'empty-review',
        'duplicate',
    ],
)
def test_unproven_utility_review_is_rejected(tmp_path, change):
    doc, occurrences = example(tmp_path)
    row = doc['rows'][0]
    if change == 'unknown-code':
        row['policy']['id'] = 'consumable:not-a-potion'
    elif change == 'wrong-identity':
        row['policy']['id'] = 'consumable:yps'
    elif change == 'wrong-recipient':
        row['policy']['recipient'] = 'player'
    elif change == 'stale-native':
        row['policy']['native_source']['sha256'] = 'bad'
    elif change == 'stale-guide':
        row['source']['sha256'] = 'bad'
    elif change == 'changed-occurrence':
        occurrences[0]['build'] = 'another-build'
    elif change == 'wrong-slot':
        occurrences[0]['slot'] = row['expected_occurrence']['slot'] = 'Helmet'
    elif change == 'wrong-bank':
        row['item_bank_target'] = 'consumable:yps'
    elif change == 'no-merc-prose':
        row['evidence']['quote'] = 'Thawing Potions and Antidote Potions.'
    elif change == 'foreign-guide':
        row['evidence']['locator'] = '/sources/other/sections/0/text'
    elif change == 'empty-review':
        row['reason'] = ''
    else:
        doc['rows'].append(copy.deepcopy(row))
    with pytest.raises(ValueError, match='utility'):
        compile_utility_source_reviews(doc, occurrences, tmp_path)


def test_completion_closes_only_the_reviewed_source_use(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs

    doc, occurrences = example(tmp_path)
    matrix, inventory = inputs()
    matrix['rows'][0]['dimensions']['market']['state'] = 'pending'
    inventory['occurrences'] = [*occurrences, {**occurrences[0], 'id': 'another-use'}]
    before = compile_completion(matrix, inventory, {'complete': True})
    after = compile_completion(matrix, inventory, {'complete': True}, utility_reviews=doc, source_root=tmp_path)
    tasks = {r['id'] for r in after['queue']}
    assert 'occurrence:potion-use' not in tasks
    assert {'occurrence:another-use', 'identity:a/market'} <= tasks
    assert after['counts']['reviewed_occurrences'] == 1
    assert not after['complete']
    assert after['scope'] != before['scope']


def corrected_player_example(tmp_path):
    doc, occurrences = example(tmp_path)
    row = doc['rows'][0]
    occurrences[0]['side'] = row['expected_occurrence']['side'] = row['source']['expected']['side'] = 'player'
    row['recipient_correction'] = 'explicit_mercenary_instruction'
    path = tmp_path / row['source']['path']
    content = json.loads(path.read_bytes())
    raw = tmp_path / occurrences[0]['source_id']
    raw.write_text(raw.read_text().replace('<h3>Mercenary</h3>', '<h3>Utilities</h3>'))
    content['sources'][occurrences[0]['source_id']] = section_inventory(raw.read_text())
    path.write_text(json.dumps(content))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row['source']['sha256'] = row['evidence']['sha256'] = digest
    return doc, occurrences


def test_explicit_mercenary_potion_prose_corrects_only_binding(tmp_path):
    doc, occurrences = corrected_player_example(tmp_path)
    before = copy.deepcopy(occurrences)
    result = compile_utility_source_reviews(doc, occurrences, tmp_path)
    assert result[0]['state'] == 'reviewed'
    assert occurrences == before


def test_player_attribution_requires_explicit_correction_review(tmp_path):
    doc, occurrences = corrected_player_example(tmp_path)
    del doc['rows'][0]['recipient_correction']
    with pytest.raises(ValueError, match='utility'):
        compile_utility_source_reviews(doc, occurrences, tmp_path)


def test_ambiguous_mercenary_mention_cannot_correct_player_attribution(tmp_path):
    doc, occurrences = corrected_player_example(tmp_path)
    row = doc['rows'][0]
    quote = 'The Mercenary needs better armor; drink Thawing Potions yourself.'
    path = tmp_path / row['source']['path']
    content = json.loads(path.read_text())
    content['sources'][occurrences[0]['source_id']]['sections'][1]['text'] = quote
    path.write_text(json.dumps(content))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row['source']['sha256'] = row['evidence']['sha256'] = digest
    row['evidence']['quote'] = quote
    with pytest.raises(ValueError, match='utility'):
        compile_utility_source_reviews(doc, occurrences, tmp_path)


def test_same_name_in_another_section_cannot_borrow_the_mercenary_quote(tmp_path):
    doc, occurrences = example(tmp_path)
    row = doc['rows'][0]
    raw = tmp_path / occurrences[0]['source_id']
    raw.write_text(raw.read_text() + '<h3>Player travel</h3><span class="d2planner-item">Thawing Potion</span>')
    guide = section_inventory(raw.read_text())
    path = tmp_path / row['source']['path']
    path.write_text(json.dumps({'sources': {occurrences[0]['source_id']: guide}}))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row['source'].update(sha256=digest, expected=guide['item_spans'][1])
    row['source']['locator'] = row['source']['locator'].replace('/item_spans/0', '/item_spans/1')
    row['evidence']['sha256'] = digest
    occurrences[0].update(side='player', source_locator='/item-spans/1')
    row['expected_occurrence'] = {k: occurrences[0].get(k) for k in FIELDS}
    row['recipient_correction'] = 'explicit_mercenary_instruction'
    with pytest.raises(ValueError, match='utility'):
        compile_utility_source_reviews(doc, occurrences, tmp_path)


def test_changed_raw_html_invalidates_the_source_position_proof(tmp_path):
    doc, occurrences = example(tmp_path)
    path = tmp_path / occurrences[0]['source_id']
    path.write_text(path.read_text() + '<p>changed source</p>')
    with pytest.raises(ValueError, match='Stale utility HTML'):
        compile_utility_source_reviews(doc, occurrences, tmp_path)
