import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_inline_source_links import inline_review
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def setup(root):
    role, occurrence = inline_review()
    role.update(
        names=['Test Unique'],
        qualities=['unique'],
        side='player',
        variant='Gear alternatives',
        slot='Weapon',
        must={'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
    )
    span = {'label': 'Test Unique', 'side': 'player', 'slot': 'Weapon'}
    path = root / role['source']['path']
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                'sources': {
                    occurrence['source_id']: {
                        'item_spans': [span] * 163,
                        'sections': [{'text': 'Weapon Test Unique: prepare the socket before use.'}],
                    }
                }
            }
        )
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    span_locator = role['source']['locator']
    role['source'].update(sha256=digest, locator=span_locator.replace('/item_spans/162', '/sections/0'))
    occurrence.update(
        name='Test Unique',
        original_label='Test Unique',
        category='unique',
        identity_status='resolved',
        side='player',
        slot='Weapon',
        variant='Guide mention',
        **{'class': 'Paladin'},
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    keys = (
        'name',
        'original_label',
        'category',
        'build',
        'variant',
        'side',
        'slot',
        'source_id',
        'source_locator',
        'class',
    )
    row = {
        'id': 'player-span',
        'kind': 'player_equipment',
        'review_date': '2026-09-27',
        'reason': 'Exact gear-table occurrence maps to the reviewed player alternative.',
        'occurrence_id': occurrence['id'],
        'expected_occurrence': {k: occurrence[k] for k in keys},
        'source': {**role['source'], 'locator': span_locator, 'expected': span},
        'evidence': {
            **role['source'],
            'locator': role['source']['locator'] + '/text',
            'quote': 'Weapon Test Unique: prepare the socket before use.',
        },
        'branches': [
            {
                'profile_id': role['id'],
                'profile_fingerprint': fingerprint(role),
                'variant': role['variant'],
                'slot': 'Weapon',
                'player_class': 'Paladin',
                'configuration_review': 'Wearer and weapon slot agree; socket preparation remains required.',
            }
        ],
        'remaining_branches': [],
    }
    return role, occurrence, {'schema_version': 1, 'rows': [row]}


def run(root, role, occurrence, doc):
    return compile_source_context_reviews(doc, [occurrence], [role], [reviewed(role, item='Test Unique')], root)


def test_explicit_player_binding_preserves_source_and_pending_branches(tmp_path):
    role, occurrence, doc = setup(tmp_path)
    saved = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == saved
    doc['rows'][0]['remaining_branches'] = ['Other socket setup still needs review.']
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'pending'


@pytest.mark.parametrize(
    'change', ['class', 'optional-class', 'slot', 'unreviewed', 'kind', 'source-slot', 'missing-class']
)
def test_player_binding_rejects_unsupported_context_even_with_fresh_profile_hash(tmp_path, change):
    role, occurrence, doc = setup(tmp_path)
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'class':
        role['must']['value'] = 'Sorceress'
    elif change == 'optional-class':
        role['must'] = {'any': [role['must'], {'op': 'fact_eq', 'field': 'identified', 'value': True}]}
    elif change == 'slot':
        role['slot'] = branch['slot'] = 'Off-Hand'
    elif change == 'unreviewed':
        branch['configuration_review'] = ''
    elif change == 'kind':
        row['kind'] = 'anything'
    elif change == 'missing-class':
        occurrence.pop('class')
        row['expected_occurrence']['class'] = None
    else:
        occurrence['slot'] = 'unspecified'
        row['expected_occurrence']['slot'] = 'unspecified'
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc)
