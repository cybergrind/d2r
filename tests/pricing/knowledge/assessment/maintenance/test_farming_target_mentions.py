"""A named farming target must not count as an equipped item recommendation."""

import copy
import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.reward_mentions import compile_reward_mentions
from tests.pricing.knowledge.assessment.maintenance.test_reward_mentions import example as reward_example


def example(
    root,
    instruction='Farm Hellfire Torches with this build to use it to its full potential!',
    name='Hellfire Torch',
    category='unique',
):
    document, occurrences = reward_example(root, slot='unspecified')
    row = document['rows'][0]
    occurrences[0].update(name=name, original_label=name, category=category)
    row['expected_occurrence'].update(name=name, original_label=name, category=category)
    gid = occurrences[0]['source_id']
    raw = root / gid
    raw.parent.mkdir(parents=True, exist_ok=True)
    html = '<h2>Summary</h2>' + instruction.replace(name, f'<span class="d2planner-item">{name}</span>')
    raw.write_text(html)
    guide = section_inventory(html)
    path = root / row['source']['path']
    path.write_text(json.dumps({'sources': {gid: guide}}))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row['kind'] = 'farming_target'
    row['reason'] = 'Explicit farm-Torches summary instruction; item appraisal and other equipped uses remain scoped.'
    row['source'].update(sha256=digest, expected=guide['item_spans'][0])
    row['evidence'].update(sha256=digest, quote=guide['sections'][1]['text'])
    row['evidence']['locator'] = row['evidence']['locator'].replace('/sections/0/', '/sections/1/')
    return document, occurrences


def test_explicit_torch_farming_goal_excludes_only_the_source_occurrence(tmp_path):
    doc, occurrences = example(tmp_path)
    before = copy.deepcopy(occurrences)
    result = compile_reward_mentions(doc, occurrences, tmp_path)
    assert result[0]['state'] == 'excluded'
    assert 'identity_id' not in result[0]
    assert occurrences == before


@pytest.mark.parametrize(
    'quote',
    [
        'Equip Hellfire Torch to improve this build.',
        'Farm gold with this build; equip Hellfire Torch.',
        'Hellfire Torch is an alternative for this build.',
    ],
)
def test_equipment_or_ambiguous_torch_prose_cannot_be_excluded(tmp_path, quote):
    doc, occurrences = example(tmp_path, quote)
    with pytest.raises(ValueError, match='reward'):
        compile_reward_mentions(doc, occurrences, tmp_path)


@pytest.mark.parametrize(
    ('name', 'category', 'quote'),
    [
        (
            'Hellfire Torch',
            'unique',
            'Ubers - This build excels at defeating the Uber Bosses and acquiring a Hellfire Torch.',
        ),
        (
            'Key of Destruction',
            'misc',
            'Nihlathak - This build excels when farming this Boss for the Key of Destruction.',
        ),
    ],
)
def test_explicit_boss_farming_target_is_not_an_equipment_requirement(tmp_path, name, category, quote):
    doc, occurrences = example(tmp_path, quote, name, category)
    assert compile_reward_mentions(doc, occurrences, tmp_path)[0]['state'] == 'excluded'


@pytest.mark.parametrize(
    ('name', 'category', 'quote'),
    [
        ('Key of Destruction', 'misc', 'Equip Key of Destruction before farming this Boss.'),
        (
            'Key of Destruction',
            'misc',
            'Farm Hellfire Torches with this build to use it to its full potential! Key of Destruction.',
        ),
        ('Key of Destruction', 'unique', 'Nihlathak - farming this Boss for the Key of Destruction.'),
        (
            'Hellfire Torch',
            'unique',
            'Equip Hellfire Torch. This build excels at defeating the Uber Bosses and acquiring a Hellfire Torch.',
        ),
        ('Key of Destruction', 'misc', 'Andariel - farming this Boss for the Key of Destruction.'),
    ],
)
def test_target_exclusion_requires_correct_item_boss_and_unambiguous_mention(tmp_path, name, category, quote):
    doc, occurrences = example(tmp_path, quote, name, category)
    with pytest.raises(ValueError, match='reward'):
        compile_reward_mentions(doc, occurrences, tmp_path)
