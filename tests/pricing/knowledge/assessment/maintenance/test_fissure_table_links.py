"""The general helmet table is distinct from the staffmod-specific Starter setup."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


def test_fissure_helmet_table_uses_general_alternatives_not_specific_setups():
    root = Path.cwd()
    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    bundle = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    result = compile_table_equivalence(doc, inventory['occurrences'], bundle['profiles'], uses, root)
    links = {r['occurrence_id']: r['profile_id'] for r in result}
    assert links.get('45f0fc9dcc3298806dd573c6') == 'fissure-druid-lore-progression-equipment'
    assert links.get('b4f06b99678df99fc7b00002') == (
        'fissure-druid-player-flickering flame-helmets-main-alternatives-helm-word-alternative'
    )


def test_reviewed_fissure_table_alternatives_retain_slot_and_use_separation():
    expected = {
        ('Ravenlore', 'Helmets'),
        ("Thundergod's Vigor", 'Belts'),
        ("Skullder's Ire", 'Body Armor'),
        ('Phoenix', 'Off-Hand'),
        ('Chance Guards', 'Gloves'),
        ('Tarnhelm', 'Helmets'),
        ("Naj's Puzzler", 'Weapon-Swap'),
        ('Earthshaker', 'Weapon'),
        ('Harmony', 'Weapon-Swap'),
        ('Sandstorm Trek', 'Boots'),
        ("Moser's Blessed Circle", 'Off-Hand'),
        ("Verdungo's Hearty Cord", 'Belts'),
        ("Ancients' Pledge", 'Off-Hand'),
        ("Natalya's Soul", 'Boots'),
        ('Wisp Projector', 'Rings'),
        ("Aldur's Advance", 'Boots'),
        ('Dwarf Star', 'Rings'),
        ("Bul-Kathos' Wedding Band", 'Rings'),
        ('Goldwrap', 'Belts'),
        ('Leaf', 'Weapon'),
        ('Bloodfist', 'Gloves'),
        ('Wealth', 'Body Armor'),
        ('Phoenix', 'Weapon'),
        ('Magefist', 'Gloves'),
        ('Peasant Crown', 'Helmets'),
        ('Lidless Wall', 'Off-Hand-Swap'),
        ('Rain', 'Body Armor'),
    }
    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    bundle = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    rows = compile_table_equivalence(doc, inventory['occurrences'], bundle['profiles'], uses, Path.cwd())
    occurrences = {o['id']: o for o in inventory['occurrences']}
    linked = {
        (o['name'], o['slot']) for row in rows if (o := occurrences[row['occurrence_id']])['build'] == 'fissure-druid'
    }
    assert expected <= linked
    # This link additionally pins the original unique planner item and its catalog.
    assert ('Flame Rift', 'Unique Charms') in linked
    rift = next(r for r in doc['rows'] if r['occurrence_id'] == '8adb46f5364167fd98200028')
    assert {e['path'] for e in rift['corroborating']} == {
        'pricing/raw/mr/planners/vf0106vk.json',
        'pricing/raw/mr/planners/game-data.json',
    }
