"""A farming reward occurrence is not an equipment recommendation or an item exclusion."""

import copy
import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.reward_mentions import compile_reward_mentions


def example(tmp_path, slot='Mephisto, Diablo, Baal'):
    span = {
        'label': 'Hellfire Torch',
        'side': 'player',
        'slot': slot,
        'item_id': '',
        'profile_id': None,
    }
    text = f'Area Rewards {slot} Hellfire Torch'
    path = tmp_path / 'pricing/data/appraisal-guide-sections.json'
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                'sources': {
                    'pricing/raw/mr/guides__zeal-paladin.html': {'item_spans': [span], 'sections': [{'text': text}]}
                }
            }
        )
    )
    ref = {
        'path': 'pricing/data/appraisal-guide-sections.json',
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    occurrence = {
        'id': 'reward-occurrence',
        'kind': 'demand',
        'name': 'Hellfire Torch',
        'original_label': 'Hellfire Torch',
        'category': 'unique',
        'build': 'zeal-paladin',
        'variant': 'Guide mention',
        'side': 'player',
        'slot': span['slot'],
        'class': 'Paladin',
        'source_id': 'pricing/raw/mr/guides__zeal-paladin.html',
        'source_locator': '/item-spans/0',
    }
    review = {
        'id': 'torch-reward',
        'kind': 'farming_reward',
        'review_date': '2026-09-27',
        'reason': (
            'Boss reward table; this occurrence does not recommend equipping the drop. Item appraisal remains in scope.'
        ),
        'occurrence_id': occurrence['id'],
        'expected_occurrence': copy.deepcopy(occurrence),
        'source': {
            **ref,
            'locator': '/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/0',
            'expected': span,
        },
        'evidence': {
            **ref,
            'locator': '/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/0/text',
            'quote': text,
        },
    }
    return {'schema_version': 1, 'rows': [review]}, [occurrence]


def test_reward_review_excludes_only_the_exact_occurrence(tmp_path):
    doc, occurrences = example(tmp_path)
    before = copy.deepcopy(occurrences)
    rows = compile_reward_mentions(doc, occurrences, tmp_path)
    assert len(rows) == 1
    assert rows[0]['occurrence_id'] == 'reward-occurrence'
    assert rows[0]['state'] == 'excluded'
    assert 'identity_id' not in rows[0]
    assert occurrences == before


@pytest.mark.parametrize(
    'change',
    [
        'wrong-kind',
        'stale-occurrence',
        'stale-hash',
        'foreign-guide',
        'no-rewards',
        'no-area',
        'no-boss',
        'no-item',
        'empty-reason',
        'duplicate',
    ],
)
def test_reward_review_rejects_unsupported_exclusion(tmp_path, change):
    doc, occurrences = example(tmp_path)
    row = doc['rows'][0]
    if change == 'wrong-kind':
        row['kind'] = 'equipment'
    elif change == 'stale-occurrence':
        occurrences[0]['slot'] = 'Helmet'
    elif change == 'stale-hash':
        row['source']['sha256'] = 'bad'
    elif change == 'foreign-guide':
        row['evidence']['locator'] = '/sources/other/sections/0/text'
    elif change == 'empty-reason':
        row['reason'] = ''
    elif change == 'duplicate':
        doc['rows'].append(copy.deepcopy(row))
    else:
        token = {
            'no-rewards': 'Rewards',
            'no-area': 'Area',
            'no-boss': 'Mephisto, Diablo, Baal',
            'no-item': 'Hellfire Torch',
        }[change]
        row['evidence']['quote'] = row['evidence']['quote'].replace(token, '').strip()
    with pytest.raises(ValueError, match=r'(?i)reward'):
        compile_reward_mentions(doc, occurrences, tmp_path)


def test_equipment_slot_cannot_be_excluded_as_a_reward(tmp_path):
    doc, occurrences = example(tmp_path, slot='Helmet')
    with pytest.raises(ValueError, match='unsupported reward occurrence'):
        compile_reward_mentions(doc, occurrences, tmp_path)


def test_completion_reward_review_preserves_item_and_other_occurrence_work(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs

    reviews, occurrences = example(tmp_path)
    occurrences[0]['identity_id'] = 'a'
    matrix, inventory = inputs()
    matrix['rows'][0]['dimensions']['market']['state'] = 'pending'
    inventory['occurrences'] = [*occurrences, {**occurrences[0], 'id': 'equipment-occurrence', 'slot': 'Unique Charms'}]
    before = compile_completion(matrix, inventory, {'complete': True})
    after = compile_completion(matrix, inventory, {'complete': True}, reward_reviews=reviews, source_root=tmp_path)
    tasks = {r['id'] for r in after['queue']}
    assert 'occurrence:reward-occurrence' not in tasks
    assert 'occurrence:equipment-occurrence' in tasks
    assert 'identity:a/market' in tasks
    assert after['counts']['excluded_occurrences'] == 1
    assert after['counts']['identities'] == 1
    assert not after['complete']
    assert before['scope'] != after['scope']
    reviews['rows'][0]['reason'] += ' Additional reviewed provenance.'
    changed = compile_completion(matrix, inventory, {'complete': True}, reward_reviews=reviews, source_root=tmp_path)
    assert changed['scope'] != after['scope']
