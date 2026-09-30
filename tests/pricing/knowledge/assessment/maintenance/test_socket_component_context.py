"""Socket filler source links must retain their actual parent HTML entry."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import setup as player_setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def setup(root, separator=' '):
    role, occurrence, doc = player_setup(root)
    name = "Guillaume's Face"
    assembly = name + ' (Cham Rune)'
    gid = occurrence['source_id']
    raw = root / gid
    raw.parent.mkdir(parents=True, exist_ok=True)
    tag = '<span class="d2planner-item">{}</span>'
    raw.write_text(
        '<h2>Gear</h2><table><tr><td>Helmets</td><td>'
        + '<br/>'.join([tag.format('Other')] * 162)
        + '<br/>'
        + tag.format(name)
        + separator
        + '('
        + tag.format('Cham Rune')
        + ')<br/></td></tr></table>'
    )
    guide = section_inventory(raw.read_text())
    cache = root / role['source']['path']
    cache.write_text(json.dumps({'sources': {gid: guide}}))
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    prefix = '/sources/' + gid.replace('~', '~0').replace('/', '~1')
    role.update(names=[name], qualities=['set'], slot='Helmets')
    role['source'].update(sha256=digest, locator=prefix + '/sections/1', quotes=[assembly])
    occurrence.update(
        name='Cham Rune', original_label='Cham Rune', category='misc', slot='Helmets', source_locator='/item-spans/163'
    )
    row = doc['rows'][0]
    row.update(kind='socket_component_reference')
    row['expected_occurrence'].update(
        name='Cham Rune', original_label='Cham Rune', category='misc', slot='Helmets', source_locator='/item-spans/163'
    )
    row['source'].update(sha256=digest, locator=prefix + '/item_spans/163', expected=guide['item_spans'][163])
    row['evidence'].update(sha256=digest, locator=prefix + '/sections/1/text', quote=assembly)
    row['branches'][0].update(
        slot='Helmets', parent_span=162, parent_label=name, assembly=assembly, profile_fingerprint=fingerprint(role)
    )
    return role, occurrence, doc


def run(root, role, occurrence, doc):
    return compile_source_context_reviews(doc, [occurrence], [role], [reviewed(role, item=role['names'][0])], root)


def test_exact_socket_entry_links_parent_without_rewriting_filler(tmp_path):
    role, occurrence, doc = setup(tmp_path)
    saved = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == saved


@pytest.mark.parametrize(
    'change', ['different-entry', 'parent-span', 'parent-name', 'count', 'class', 'role-parent', 'missing-review']
)
def test_socket_link_rejects_nearby_or_incompatible_parent(tmp_path, change):
    role, occurrence, doc = setup(tmp_path, '<br/>' if change == 'different-entry' else ' ')
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'parent-span':
        branch['parent_span'] = 161
    elif change == 'parent-name':
        branch['parent_label'] = 'Other'
    elif change == 'count':
        branch['assembly'] = "Guillaume's Face (2x Cham Runes)"
    elif change == 'class':
        role['must']['value'] = 'Sorceress'
    elif change == 'role-parent':
        role['names'] = ['Other']
    elif change == 'missing-review':
        branch['configuration_review'] = ''
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match=r'(?i)source-context'):
        run(tmp_path, role, occurrence, doc)
