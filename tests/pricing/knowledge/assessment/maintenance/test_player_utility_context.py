"""Footnote use wins over a generic table slot, with explicit supporting text."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import setup as player_setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


EXAMPLES = (
    ('Demon Limb', 'unique', 'Prebuff', 'enchant_prebuff', 'Demon Limb pre-buffs Enchant for increased Attack Rating.'),
    ('Treachery', 'runeword', 'Prebuff', 'fade_prebuff', 'Treachery pre-buffs Fade for All Resistances.'),
    (
        'Wizardspike',
        'unique',
        'Weapon-Swap',
        'casting_swap',
        'Wizardspike is used for the Faster Cast Rate it provides on Weapon-Swap '
        'prior to acquiring a Call to Arms, or if Barbarian-granted Battle Orders is available.',
    ),
    (
        "Naj's Puzzler",
        'set',
        'Weapon-Swap',
        'teleport_swap',
        "Only use Naj's Puzzler for Teleport Charges if you are not using Enigma.",
    ),
)


def setup(root, example):
    name, quality, slot, purpose, quote = example
    role, occurrence, doc = player_setup(root)
    gid = occurrence['source_id']
    raw = root / gid
    raw.parent.mkdir(parents=True, exist_ok=True)
    tag = f'<span class="d2planner-item" data-d2planner-profile="planner" data-d2planner-id="7">{name}</span>'
    raw.write_text('<h2>Gear</h2>' + tag * 162 + '<h2>Utility</h2>' + quote.replace(name, tag))
    guide = section_inventory(raw.read_text())
    cache = root / role['source']['path']
    cache.write_text(json.dumps({'sources': {gid: guide}}))
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    prefix = '/sources/' + gid.replace('~', '~0').replace('/', '~1')
    role.update(names=[name], qualities=['normal'] if quality == 'runeword' else [quality], slot=slot)
    if quality == 'runeword':
        role['must'] = {'all': [role['must'], {'op': 'fact_eq', 'field': 'runeword', 'value': name}]}
    role['source'].update(sha256=digest, locator=prefix + '/sections/2', quotes=[quote])
    occurrence.update(name=name, original_label=name, category=quality, slot='unspecified')
    row = doc['rows'][0]
    row.update(kind='player_utility_reference')
    row['expected_occurrence'].update(name=name, original_label=name, category=quality, slot='unspecified')
    row['source'].update(sha256=digest, expected=guide['item_spans'][162])
    row['evidence'].update(sha256=digest, locator=prefix + '/sections/2/text', quote=quote)
    row['branches'][0].update(slot=slot, utility_kind=purpose, profile_fingerprint=fingerprint(role))
    return role, occurrence, doc


def run(root, role, occurrence, doc):
    return compile_source_context_reviews(doc, [occurrence], [role], [reviewed(role, item=occurrence['name'])], root)


@pytest.mark.parametrize('example', EXAMPLES)
def test_utility_reference_preserves_original_slot_and_specific_use(tmp_path, example):
    role, occurrence, doc = setup(tmp_path, example)
    original = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == original


@pytest.mark.parametrize(
    'change',
    [
        'combat-slot',
        'mercenary',
        'wrong-purpose',
        'wrong-class',
        'empty-review',
        'name-only',
        'wrong-section',
        'wrong-primary',
    ],
)
def test_utility_link_cannot_erase_semantic_conditions(tmp_path, change):
    role, occurrence, doc = setup(tmp_path, EXAMPLES[0])
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'combat-slot':
        role['slot'] = branch['slot'] = 'Weapon'
    elif change == 'mercenary':
        role['side'] = 'merc'
    elif change == 'wrong-purpose':
        branch['utility_kind'] = 'fade_prebuff'
    elif change == 'wrong-class':
        role['must']['value'] = 'Sorceress'
    elif change == 'empty-review':
        branch['configuration_review'] = ''
    elif change == 'name-only':
        row['evidence']['quote'] = occurrence['name']
    elif change == 'wrong-section':
        row['evidence']['locator'] = row['evidence']['locator'].replace('/sections/2/', '/sections/1/')
        row['evidence']['quote'] = occurrence['name']
    else:
        role['source']['locator'] = role['source']['locator'].replace('/sections/2', '/sections/1')
        role['source']['quotes'] = [occurrence['name']]
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc)
