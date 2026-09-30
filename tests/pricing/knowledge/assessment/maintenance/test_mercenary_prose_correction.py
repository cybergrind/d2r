"""Correct the wearer of an exact, explicit mercenary instruction without rewriting evidence."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import run, setup as player_setup


QUOTE = 'Use a Desert Mercenary with Might Aura. Equip him with Test Unique for its useful effect.'


def setup(root, quote=QUOTE):
    role, occurrence, document = player_setup(root)
    role.update(side='merc', slot='Weapon')
    role['must'] = {'all': [role['must'], {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'}]}
    occurrence.update(side='player', slot='unspecified')
    path = root / role['source']['path']
    data = json.loads(path.read_text())
    guide = data['sources'][occurrence['source_id']]
    for span in guide['item_spans']:
        span.update(side='player', slot='unspecified')
    guide['sections'][0]['text'] = quote
    path.write_text(json.dumps(data))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    role['source']['sha256'] = digest
    row = document['rows'][0]
    row.update(kind='mercenary_prose_correction')
    row['expected_occurrence'].update(side='player', slot='unspecified')
    row['source'].update(sha256=digest, expected=guide['item_spans'][162])
    row['evidence'].update(sha256=digest, quote=quote)
    row['branches'][0].update(
        slot='Weapon',
        mercenary_type='Act 2 Might',
        profile_fingerprint=fingerprint(role),
        configuration_review='Explicit equip-him mercenary instruction, not player equipment.',
    )
    return role, occurrence, document


def test_explicit_mercenary_prose_corrects_only_the_review_binding(tmp_path):
    role, occurrence, document = setup(tmp_path)
    original = deepcopy(occurrence)
    result = run(tmp_path, role, occurrence, document)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_ids'] == [role['id']]
    assert occurrence == original


@pytest.mark.parametrize(
    'quote',
    [
        'Use Might Aura. Equip him with Test Unique.',
        'Use a Desert Mercenary with Might Aura. Equip yourself with Test Unique.',
        'Use a Desert Mercenary with Holy Freeze Aura. Equip him with Test Unique.',
    ],
)
def test_ambiguous_or_player_prose_cannot_change_wearer(tmp_path, quote):
    role, occurrence, document = setup(tmp_path, quote)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, document)


@pytest.mark.parametrize(
    'change',
    ['player-role', 'wrong-slot', 'wrong-class', 'wrong-merc', 'optional-merc', 'missing-review', 'already-merc'],
)
def test_wearer_correction_requires_exact_reviewed_context(tmp_path, change):
    role, occurrence, document = setup(tmp_path)
    branch = document['rows'][0]['branches'][0]
    if change == 'player-role':
        role['side'] = 'player'
    elif change == 'wrong-slot':
        role['slot'] = branch['slot'] = 'Helmet'
    elif change == 'wrong-class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'wrong-merc':
        role['must']['all'][1]['value'] = 'Act 2 Holy Freeze'
    elif change == 'optional-merc':
        role['must']['all'][1] = {
            'any': [role['must']['all'][1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'missing-review':
        branch['configuration_review'] = ''
    else:
        occurrence['side'] = document['rows'][0]['expected_occurrence']['side'] = 'merc'
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, document)
