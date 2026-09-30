import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import run, setup as player_setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


TYPES = ['Act 2 Might', 'Act 5 Frenzy']


def merc(types):
    return {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': value} for value in types]}


def setup(root):
    role, occurrence, document = player_setup(root)
    role.update(side='merc', slot='Body Armor')
    role['must'] = {'all': [role['must'], merc(TYPES)]}
    occurrence.update(side='merc', slot='Body Armor')
    path = root / role['source']['path']
    data = json.loads(path.read_text())
    guide = data['sources'][occurrence['source_id']]
    for span in guide['item_spans']:
        span.update(side='merc', slot='Body Armor')
    quote = 'Early-game Body Armor Test Unique: Act 2 Might or Act 5 Frenzy.'
    guide['sections'][0]['text'] = quote
    path.write_text(json.dumps(data))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    role['source']['sha256'] = digest
    row = document['rows'][0]
    row.update(kind='mercenary_equipment', mercenary_types=list(TYPES))
    row['expected_occurrence'].update(side='merc', slot='Body Armor')
    row['source'].update(sha256=digest, expected=guide['item_spans'][162])
    row['evidence'].update(sha256=digest, quote=quote)
    row['branches'][0].update(
        slot='Body Armor',
        mercenary_types=list(TYPES),
        profile_fingerprint=fingerprint(role),
        configuration_review='Both explicit early-game mercenary alternatives are reviewed.',
    )
    return role, occurrence, document


def test_explicit_multi_mercenary_equipment_binding_preserves_occurrence(tmp_path):
    role, occurrence, document = setup(tmp_path)
    original = deepcopy(occurrence)
    result = run(tmp_path, role, occurrence, document)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_ids'] == [role['id']]
    assert occurrence == original


def test_separate_roles_can_cover_all_declared_mercenaries(tmp_path):
    original, occurrence, document = setup(tmp_path)
    row = document['rows'][0]
    branch = row['branches'][0]
    roles, branches = [], []
    for index, mercenary in enumerate(TYPES):
        role = deepcopy(original)
        role['id'] += f'-{index}'
        role['must']['all'][1] = merc([mercenary])
        roles.append(role)
        branches.append(
            {
                **branch,
                'profile_id': role['id'],
                'profile_fingerprint': fingerprint(role),
                'mercenary_types': [mercenary],
            }
        )
    row['branches'] = branches
    result = compile_source_context_reviews(
        document,
        [occurrence],
        roles,
        [reviewed(role, item='Test Unique') for role in roles],
        tmp_path,
    )
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_ids'] == sorted(role['id'] for role in roles)


@pytest.mark.parametrize('pending', [False, True])
def test_one_branch_cannot_close_a_two_mercenary_recommendation(tmp_path, pending):
    role, occurrence, document = setup(tmp_path)
    row = document['rows'][0]
    role['must']['all'][1] = merc(['Act 2 Might'])
    row['branches'][0].update(mercenary_types=['Act 2 Might'], profile_fingerprint=fingerprint(role))
    if pending:
        row['remaining_branches'] = ['Act 5 Frenzy has not been reviewed.']
        assert run(tmp_path, role, occurrence, document)[0]['state'] == 'pending'
    else:
        with pytest.raises(ValueError, match='source-context'):
            run(tmp_path, role, occurrence, document)


@pytest.mark.parametrize(
    'change',
    [
        'missing-types',
        'duplicate-types',
        'optional-mercenary',
        'wrong-role-types',
        'incomplete-quote',
        'wrong-slot',
        'wrong-class',
        'empty-review',
        'duplicate-branches',
    ],
)
def test_mercenary_equipment_binding_requires_complete_exact_context(tmp_path, change):
    role, occurrence, document = setup(tmp_path)
    row = document['rows'][0]
    branch = row['branches'][0]
    if change == 'missing-types':
        row.pop('mercenary_types')
    elif change == 'duplicate-types':
        row['mercenary_types'].append('Act 2 Might')
    elif change == 'optional-mercenary':
        role['must']['all'][1] = {'any': [merc(TYPES), {'op': 'fact_eq', 'field': 'identified', 'value': True}]}
    elif change == 'wrong-role-types':
        role['must']['all'][1] = merc(['Act 5 Bash'])
    elif change == 'incomplete-quote':
        row['evidence']['quote'] = row['evidence']['quote'].split(' or ')[0]
    elif change == 'wrong-slot':
        role['slot'] = branch['slot'] = 'Helmet'
    elif change == 'wrong-class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'empty-review':
        branch['configuration_review'] = ''
    elif change == 'duplicate-branches':
        row['branches'].append(deepcopy(branch))
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, document)


def test_review_can_explicitly_select_one_supported_branch_of_a_broader_role(tmp_path):
    role, occurrence, document = setup(tmp_path)
    row = document['rows'][0]
    row['mercenary_types'] = ['Act 2 Might']
    row['branches'][0].update(mercenary_types=['Act 2 Might'], role_mercenary_types=list(TYPES))
    assert run(tmp_path, role, occurrence, document)[0]['state'] == 'reviewed'
    assert row['branches'][0]['role_mercenary_types'] == TYPES


@pytest.mark.parametrize(
    'change', ['no-explicit-role-scope', 'stale-role-scope', 'unsupported-branch', 'duplicate-role-types']
)
def test_narrow_source_binding_cannot_invent_or_hide_role_context(tmp_path, change):
    role, occurrence, document = setup(tmp_path)
    row = document['rows'][0]
    row['mercenary_types'] = ['Act 2 Might']
    branch = row['branches'][0]
    branch.update(mercenary_types=['Act 2 Might'], role_mercenary_types=list(TYPES))
    if change == 'no-explicit-role-scope':
        branch.pop('role_mercenary_types')
    elif change == 'stale-role-scope':
        branch['role_mercenary_types'] = ['Act 2 Might']
    elif change == 'unsupported-branch':
        branch['mercenary_types'] = ['Act 5 Bash']
    else:
        branch['role_mercenary_types'].append('Act 2 Might')
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, document)
