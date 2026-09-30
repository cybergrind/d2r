"""Hardcore prose exclusions must preserve adjacent Softcore uses of the same item."""

import copy
import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.hardcore_mentions import compile_hardcore_mentions
from pricing.knowledge.assessment.maintenance.reward_mentions import FIELDS


HTML = """<h2>Standard</h2><span class="d2planner-item">Enigma</span>
<h3>Hardcore</h3><p>Review the changes below for Hardcore.</p>
<h3>Gear Changes</h3><p>Use <span class="d2planner-item">Enigma</span> here.</p>
<h2>Summary</h2><span class="d2planner-item">Enigma</span>"""
GUIDE = 'pricing/raw/mr/guides__zeal-paladin.html'
PREFIX = '/sources/pricing~1raw~1mr~1guides__zeal-paladin.html'


def example(root, html=HTML):
    raw = root / GUIDE
    raw.parent.mkdir(parents=True)
    raw.write_text(html)
    guide = section_inventory(html)
    path = root / 'pricing/data/appraisal-guide-sections.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'sources': {GUIDE: guide}}))
    occurrences = [
        dict(
            id=f'item-{i}',
            kind='demand',
            name='Enigma',
            original_label='Enigma',
            category='runeword',
            build='zeal-paladin',
            variant='Guide mention',
            side=span['side'],
            slot=span['slot'],
            source_id=GUIDE,
            source_locator=f'/item-spans/{i}',
            identity_id='enigma',
            **{'class': 'Paladin'},
        )
        for i, span in enumerate(guide['item_spans'])
    ]
    row = {
        'id': 'hc-enigma',
        'occurrence_id': 'item-1',
        'review_date': '2026-09-27',
        'reason': 'Explicit Hardcore gear-change section; adjacent Standard and summary mentions remain scoped.',
        'expected_occurrence': {k: occurrences[1].get(k) for k in FIELDS},
        'source': {
            'path': str(path.relative_to(root)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'locator': PREFIX + '/item_spans/1',
            'expected': guide['item_spans'][1],
        },
        'section_range': {
            'start': 2,
            'stop': 4,
            'start_heading': 'Hardcore',
            'stop_heading': 'Summary',
            'quote': 'Review the changes below for Hardcore.',
        },
    }
    return {'schema_version': 1, 'rows': [row]}, occurrences


def test_exact_hardcore_occurrence_does_not_exclude_the_item_or_softcore_mentions(tmp_path):
    document, occurrences = example(tmp_path)
    before = copy.deepcopy(occurrences)
    result = compile_hardcore_mentions(document, occurrences, tmp_path)
    assert [r['occurrence_id'] for r in result] == ['item-1']
    assert result[0]['state'] == 'excluded'
    assert 'identity_id' not in result[0]
    assert occurrences == before


@pytest.mark.parametrize('index', [0, 2])
def test_same_item_outside_reviewed_hardcore_section_cannot_be_excluded(tmp_path, index):
    document, occurrences = example(tmp_path)
    row = document['rows'][0]
    row.update(occurrence_id=f'item-{index}', expected_occurrence={k: occurrences[index].get(k) for k in FIELDS})
    row['source']['locator'] = PREFIX + f'/item_spans/{index}'
    row['source']['expected']['side'] = occurrences[index]['side']
    with pytest.raises(ValueError, match='Hardcore'):
        compile_hardcore_mentions(document, occurrences, tmp_path)


@pytest.mark.parametrize('change', ['raw', 'cache', 'identity', 'start', 'stop', 'quote', 'reason', 'duplicate'])
def test_changed_or_unsupported_exclusion_is_rejected(tmp_path, change):
    document, occurrences = example(tmp_path)
    row = document['rows'][0]
    if change == 'raw':
        (tmp_path / GUIDE).write_text(HTML + 'changed')
    elif change == 'cache':
        row['source']['sha256'] = 'stale'
    elif change == 'identity':
        occurrences[1]['original_label'] = 'Spirit'
    elif change == 'start':
        row['section_range']['start'] = 1
    elif change == 'stop':
        row['section_range']['stop_heading'] = 'Other'
    elif change == 'quote':
        row['section_range']['quote'] = 'unsupported'
    elif change == 'reason':
        row['reason'] = ''
    else:
        document['rows'].append(copy.deepcopy(row))
    with pytest.raises(ValueError, match='Hardcore'):
        compile_hardcore_mentions(document, occurrences, tmp_path)


def test_completion_keeps_softcore_mentions_and_identity_work(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs

    document, occurrences = example(tmp_path)
    matrix, inventory = inputs()
    matrix['rows'][0]['dimensions']['market']['state'] = 'pending'
    inventory['occurrences'] = [{**r, 'identity_id': 'a'} for r in occurrences]
    before = compile_completion(matrix, inventory, {'complete': True})
    after = compile_completion(matrix, inventory, {'complete': True}, hardcore_reviews=document, source_root=tmp_path)
    tasks = {r['id'] for r in after['queue']}
    assert 'occurrence:item-1' not in tasks
    assert {'occurrence:item-0', 'occurrence:item-2', 'identity:a/market'} <= tasks
    assert after['counts']['excluded_occurrences'] == 1
    assert after['counts']['identities'] == 1
    assert not after['complete']
    assert before['scope'] != after['scope']
    document['rows'][0]['reason'] += ' Preserved source separation.'
    changed = compile_completion(matrix, inventory, {'complete': True}, hardcore_reviews=document, source_root=tmp_path)
    assert changed['scope'] != after['scope']


def test_original_html_positions_survive_entity_unescaping(tmp_path):
    document, occurrences = example(tmp_path, HTML.replace('<h3>Gear Changes', '&amp; ' * 30 + '<h3>Gear Changes'))
    assert compile_hardcore_mentions(document, occurrences, tmp_path)[0]['occurrence_id'] == 'item-1'


def test_review_cannot_extend_past_summary_into_softcore_advice(tmp_path):
    document, occurrences = example(tmp_path, HTML + '<h2>Credits</h2>')
    document['rows'][0]['section_range'].update(stop=5, stop_heading='Credits')
    with pytest.raises(ValueError, match='Hardcore'):
        compile_hardcore_mentions(document, occurrences, tmp_path)


def test_mechanics_section_ends_hardcore_advice(tmp_path):
    html = HTML.replace('<h2>Summary</h2>', '<h2>Mechanics</h2>') + '<h2>Summary</h2>'
    document, occurrences = example(tmp_path, html)
    document['rows'][0]['section_range'].update(stop_heading='Mechanics')
    assert compile_hardcore_mentions(document, occurrences, tmp_path)[0]['occurrence_id'] == 'item-1'
    row = document['rows'][0]
    row.update(occurrence_id='item-2', expected_occurrence={k: occurrences[2].get(k) for k in FIELDS})
    row['source']['locator'] = PREFIX + '/item_spans/2'
    with pytest.raises(ValueError, match='Hardcore'):
        compile_hardcore_mentions(document, occurrences, tmp_path)


def test_hardcore_review_cannot_swallow_intervening_mechanics(tmp_path):
    html = HTML.replace('<h2>Summary</h2>', '<h2>Mechanics</h2>') + '<h2>Summary</h2>'
    document, occurrences = example(tmp_path, html)
    document['rows'][0]['section_range'].update(stop=5, stop_heading='Summary')
    with pytest.raises(ValueError, match='Hardcore'):
        compile_hardcore_mentions(document, occurrences, tmp_path)
