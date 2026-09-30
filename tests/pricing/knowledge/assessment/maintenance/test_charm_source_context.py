"""Resolved charm bases need typed pattern reviews, not named-item exemptions."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import OCCURRENCE_FIELDS
from tests.pricing.knowledge.assessment.maintenance.test_pattern_source_context import pattern_setup, run


CHARMS = (('Small Charm', 'cm1', 'scha'), ('Large Charm', 'cm2', 'mcha'), ('Grand Charm', 'cm3', 'lcha'))


def setup(root, name, code, item_type):
    role, occurrence, doc, use = pattern_setup(root)
    occurrence.update(name=name, original_label=name, category='misc', identity_status='resolved', slot='Charms')
    role.update(types=[item_type], qualities=['magic'], slot='Charms')
    role['must'] = {'all': [role['must'], {'op': 'fact_eq', 'field': 'base_code', 'value': code}]}
    row = doc['rows'][0]
    row['kind'] = 'player_charm_pattern'
    row['expected_occurrence'] = {k: occurrence.get(k) for k in (*OCCURRENCE_FIELDS, 'class')}
    span = {'label': name, 'side': 'player', 'slot': 'Charms'}
    path = root / role['source']['path']
    payload = json.loads(path.read_text())
    payload['sources'][occurrence['source_id']]['item_spans'][162] = span
    payload['sources'][occurrence['source_id']]['sections'][0]['text'] = 'Charms: ' + name + ' with resistance.'
    path.write_text(json.dumps(payload))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    role['source'].update(sha256=digest, locator=row['source']['locator'])
    row['source'].update(sha256=digest, expected=span)
    row['evidence'].update(sha256=digest, quote=name)
    row['branches'][0].update(slot='Charms', pattern_label=name, profile_fingerprint=fingerprint(role))
    use.update(source=deepcopy(role['source']), profile_fingerprint=fingerprint(role), pattern_label=name)
    return role, occurrence, doc, use


@pytest.mark.parametrize(('name', 'code', 'item_type'), CHARMS)
def test_typed_charm_review_preserves_resolved_identity(tmp_path, name, code, item_type):
    args = setup(tmp_path, name, code, item_type)
    original = deepcopy(args[1])
    assert run(tmp_path, *args)[0]['state'] == 'reviewed'
    assert args[1] == original
    args[2]['rows'][0]['remaining_branches'] = ['Another charm use still needs review.']
    assert run(tmp_path, *args)[0]['state'] == 'pending'


@pytest.mark.parametrize(
    'change', ['type', 'base', 'optional-base', 'quality', 'named', 'unresolved', 'wrong-kind', 'primary']
)
def test_typed_charm_review_rejects_broad_or_mismatched_rules(tmp_path, change):
    role, occurrence, doc, use = setup(tmp_path, *CHARMS[0])
    row = doc['rows'][0]
    if change == 'type':
        role['types'] = ['lcha']
    elif change == 'base':
        role['must']['all'][1]['value'] = 'cm3'
    elif change == 'optional-base':
        role['must']['all'][1] = {
            'any': [role['must']['all'][1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'quality':
        role['qualities'] = row['branches'][0]['qualities'] = ['unique']
    elif change == 'named':
        role['names'] = ['Annihilus']
    elif change == 'unresolved':
        occurrence.update(identity_status='unresolved')
    elif change == 'wrong-kind':
        row['kind'] = 'player_pattern'
    elif change == 'primary':
        role['source']['locator'] = role['source']['locator'].replace('/item_spans/162', '/sections/0')
    row['branches'][0]['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    use['source'] = deepcopy(role['source'])
    with pytest.raises(ValueError, match=r'source-context|Stale guide-use'):
        run(tmp_path, role, occurrence, doc, use)
