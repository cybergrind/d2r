"""Named prose links retain inventory ownership and upgrade preparation."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_utility_context import setup as utility_setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def run(root, role, occurrence, doc):
    return compile_source_context_reviews(doc, [occurrence], [role], [reviewed(role, item=role['names'][0])], root)


BONE = 'Dealing exclusively Physical Damage, the build benefits when using Bone Break.'
UBERS = "Along with Bone Break, Decrepify also allows you destroy Uber Baal's Physical Immune summons."
BUTCHER = "An Upgraded Butcher's Pupil is a strong, relatively easy to acquire weapon."


def setup(root, butcher=False, merc=False):
    name = "Butcher's Pupil" if butcher else 'Bone Break'
    quote = BUTCHER if butcher else UBERS if merc else BONE
    slot = 'Weapon' if butcher else 'Unique Charms'
    role, occurrence, doc = utility_setup(root, (name, 'unique', slot, '', quote))
    row = doc['rows'][0]
    row['kind'] = 'qualified_named_prose'
    branch = row['branches'][0]
    branch.pop('utility_kind')
    if butcher:
        role['source']['quotes'] = [name + ' (Upgraded)']
        # Keep a reviewed upgrade source separate from the prose being bound.
        path = root / role['source']['path']
        data = json.loads(path.read_text())
        data['sources'][occurrence['source_id']]['sections'][0]['text'] = name + ' (Upgraded)'
        path.write_text(json.dumps(data))
        role['source']['locator'] = role['source']['locator'].replace('/sections/2', '/sections/0')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        role['source']['sha256'] = row['source']['sha256'] = row['evidence']['sha256'] = digest
        branch['upgrade_base_code'] = 'reviewed-upgrade'
        role['depends_on'] = [
            {
                'label': 'Upgraded base required.',
                'when': {'op': 'fact_eq', 'field': 'base_code', 'value': 'reviewed-upgrade'},
            }
        ]
    if merc:
        raw = root / occurrence['source_id']
        raw.write_text(raw.read_text().replace('<h2>Utility</h2>', '<h2>Mercenary</h2>'))
        guide = section_inventory(raw.read_text())
        path = root / role['source']['path']
        path.write_text(json.dumps({'sources': {occurrence['source_id']: guide}}))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        role['source']['sha256'] = row['source']['sha256'] = row['evidence']['sha256'] = digest
        occurrence['side'] = row['expected_occurrence']['side'] = 'merc'
        row['source']['expected'] = guide['item_spans'][162]
    branch['profile_fingerprint'] = fingerprint(role)
    return role, occurrence, doc


@pytest.mark.parametrize(('butcher', 'merc'), [(False, False), (False, True), (True, False)])
def test_named_instruction_preserves_upgrade_or_player_inventory_use(tmp_path, butcher, merc):
    role, occurrence, doc = setup(tmp_path, butcher, merc)
    saved = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == saved


@pytest.mark.parametrize('change', ['role-slot', 'role-side', 'class', 'name-only', 'renamed-charm', 'empty-review'])
def test_charm_link_cannot_become_mercenary_equipment_or_another_charm(tmp_path, change):
    role, occurrence, doc = setup(tmp_path)
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'role-slot':
        role['slot'] = branch['slot'] = 'Weapon'
    elif change == 'role-side':
        role['side'] = 'merc'
    elif change == 'class':
        role['must']['value'] = 'Sorceress'
    elif change == 'name-only':
        row['evidence']['quote'] = 'Bone Break'
    elif change == 'renamed-charm':
        role['names'] = ['Renewed Bone Break']
    else:
        branch['configuration_review'] = ''
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'(?i)source-context'):
        run(tmp_path, role, occurrence, doc)


def test_upgrade_prose_requires_the_reviewed_upgrade_condition(tmp_path):
    role, occurrence, doc = setup(tmp_path, butcher=True)
    role['depends_on'] = []
    doc['rows'][0]['branches'][0]['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'(?i)source-context'):
        run(tmp_path, role, occurrence, doc)


def cta_setup(root):
    quote = 'Start by casting Battle Command twice, then Battle Orders from Call to Arms.'
    role, occurrence, doc = utility_setup(root, ('Call to Arms', 'runeword', 'Weapon-Swap', '', quote))
    role['important_stats'] = ['97:149', '97:155', '127:0']
    row = doc['rows'][0]
    row['kind'] = 'qualified_named_prose'
    row['branches'][0].pop('utility_kind')
    row['branches'][0]['profile_fingerprint'] = fingerprint(role)
    return role, occurrence, doc


def test_named_prebuff_instruction_binds_reviewed_swap_without_claiming_active_buffs(tmp_path):
    role, occurrence, doc = cta_setup(tmp_path)
    original = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == original


@pytest.mark.parametrize('change', ['main-weapon', 'missing-bo', 'missing-bc', 'name-only', 'mercenary'])
def test_cta_prebuff_reference_requires_swap_and_both_buff_contributions(tmp_path, change):
    role, occurrence, doc = cta_setup(tmp_path)
    row = doc['rows'][0]
    if change == 'main-weapon':
        role['slot'] = row['branches'][0]['slot'] = 'Weapon'
    elif change == 'missing-bo':
        role['important_stats'].remove('97:149')
    elif change == 'missing-bc':
        role['important_stats'].remove('97:155')
    elif change == 'name-only':
        row['evidence']['quote'] = 'Call to Arms'
    else:
        role['side'] = 'merc'
    row['branches'][0]['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'(?i)source-context'):
        run(tmp_path, role, occurrence, doc)
