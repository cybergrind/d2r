"""Narrative reviews must bind the particular Cube mention, not just its section."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.carried_cube_reviews import occurrence_fingerprint
from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.cube_narrative_reviews import compile_cube_narrative_reviews
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


GUIDE = 'pricing/raw/mr/guides__example.html'
CACHE = 'pricing/data/appraisal-guide-sections.json'
STORAGE = (
    'Keep a Lower Resist Charge Wand in your inventory and/or Horadric Cube '
    'to break monster Fire Immunity/lower monster Fire Resistances if necessary.'
)
RECHARGE = 'Recharge this Wand as needed using Gold or the Chipped Gem + Ort Rune Horadric Cube Recipe.'


def example(root, first=STORAGE, classification='storage_context'):
    html = (
        '<h3>Strategy</h3><p>'
        + (first + ' ' + RECHARGE).replace('Horadric Cube', '<span class="d2planner-item">Horadric Cube</span>')
        + '</p>'
    )
    inputs = {}
    for name, raw in ((GUIDE, html), (CACHE, json.dumps({'sources': {GUIDE: section_inventory(html)}}))):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
        inputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    occurrences = []
    for idx in range(2):
        occurrences.append(
            {
                'id': str(idx),
                'identity_id': 'cube',
                'name': 'Horadric Cube',
                'original_label': 'Horadric Cube',
                'kind': 'demand',
                'category': 'misc',
                'variant': 'Guide mention',
                'side': 'player',
                'slot': 'unspecified',
                'source_id': GUIDE,
                'source_locator': f'/item-spans/{idx}',
                'identity_status': 'resolved',
                'source_status': 'verified',
                'details': {'role': 'guide_mention'},
            }
        )
    inventory = {
        'identities': [{'id': 'cube', 'name': 'Horadric Cube', 'category': 'misc'}],
        'occurrences': occurrences,
        'sources': [
            {'id': GUIDE, 'path': GUIDE, 'status': 'verified', 'sha256': inputs[GUIDE], 'actual_sha256': inputs[GUIDE]}
        ],
    }
    review = {
        'schema_version': 1,
        'scope': 'horadric_cube_narrative_only',
        'inputs': inputs,
        'rows': [
            {
                'occurrence_id': '0',
                'occurrence_sha256': occurrence_fingerprint(occurrences[0]),
                'section_index': 1,
                'quote': first.replace('Horadric Cube', '@CUBE@Horadric Cube'),
                'classification': classification,
                'reviewed_at': '2026-09-30',
                'reason': 'Carried storage container; referenced wand assessment remains independent.',
            }
        ],
    }
    return inventory, review


def test_review_binds_exact_cube_without_closing_neighbor_or_identity(tmp_path):
    inventory, review = example(tmp_path)
    original = deepcopy(inventory)
    result = compile_cube_narrative_reviews(review, inventory, tmp_path)
    assert result[0]['state'] == 'reviewed'
    completed = compile_completion(
        {'rows': []}, inventory, {'complete': True}, cube_narrative_reviews=review, source_root=tmp_path
    )
    ids = {r['id'] for r in completed['queue']}
    assert 'occurrence:0' not in ids
    assert {'occurrence:1', 'identity:cube', 'final:verification'} <= ids
    assert not completed['complete']
    assert inventory == original


@pytest.mark.parametrize(
    'mutation',
    [
        'neighbor-quote',
        'wrong-class',
        'wrong-section',
        'stale',
        'missing',
        'wrong-name',
        'wrong-side',
        'duplicate',
        'missing-identity',
    ],
)
def test_invalid_narrative_review_fails(tmp_path, mutation):
    inventory, review = example(tmp_path)
    row = review['rows'][0]
    if mutation == 'neighbor-quote':
        row.update(
            quote=RECHARGE.replace('Horadric Cube', '@CUBE@Horadric Cube'), classification='recharge_recipe_context'
        )
    elif mutation == 'wrong-class':
        row['classification'] = 'recharge_recipe_context'
    elif mutation == 'wrong-section':
        row['section_index'] = 0
    elif mutation == 'stale':
        (tmp_path / GUIDE).write_text('changed')
    elif mutation == 'missing':
        (tmp_path / GUIDE).unlink()
    elif mutation == 'duplicate':
        review['rows'].append(deepcopy(row))
    elif mutation == 'missing-identity':
        inventory['identities'] = []
    else:
        inventory['occurrences'][0]['name' if mutation == 'wrong-name' else 'side'] = 'other'
        row['occurrence_sha256'] = occurrence_fingerprint(inventory['occurrences'][0])
    with pytest.raises(ValueError, match='Cube'):
        compile_cube_narrative_reviews(review, inventory, tmp_path)


@pytest.mark.parametrize(
    ('quote', 'classification'),
    [
        (RECHARGE, 'recharge_recipe_context'),
        (
            'Repair this Wand with Gold or the Chipped Gem + Ort Rune Horadric Cube recipe to regain the Charges.',
            'recharge_recipe_context',
        ),
        ('Upgrade your Boots to the highest base possible, using the Horadric Cube recipe.', 'upgrade_recipe_context'),
    ],
)
def test_recipe_context_reviews_do_not_close_the_recipe_or_equipment(tmp_path, quote, classification):
    inventory, review = example(tmp_path, quote, classification)
    result = compile_cube_narrative_reviews(review, inventory, tmp_path)
    assert [(r['occurrence_id'], r['classification']) for r in result] == [('0', classification)]
