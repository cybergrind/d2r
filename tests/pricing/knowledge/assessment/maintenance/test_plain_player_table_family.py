"""Independent cross-build samples preserve each table item's actual equipment slot."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


EXPECTED = {
    ('berserk-barbarian', "Naj's Puzzler", 'Weapon-Swap'),
    ('blessed-hammer-paladin', 'Principle', 'Body Armors'),
    ('blizzard-sorceress', 'Lore', 'Helmets'),
    ('double-throw-barbarian-guide', 'Wraith Flight', 'Off-Hand'),
    ('dragon-talon-assassin', 'String of Ears', 'Belts'),
    ('dream-paladin', 'Bloodfist', 'Gloves'),
    ('echoing-strike-warlock-guide', 'Lore', 'Helmets'),
    ('enchant-sorceress', "Sander's Riprap", 'Boots'),
    ('fire-blast-assassin', "Bul-Kathos' Wedding Band", 'Rings'),
    ('fire-warlock-guide', "Ondal's Wisdom", 'Weapon'),
    ('fist-of-the-heavens-paladin', 'Principle', 'Body Armors'),
    ('gold-find-barbarian', 'Wizardspike', 'Off-Hand-Swap'),
    ('lightning-fury-amazon-guide', 'Peasant Crown', 'Helmets'),
    ('lightning-sentry-assassin', "Bul-Kathos' Wedding Band", 'Rings'),
    ('lightning-sorceress', 'Obsession', 'Weapon'),
    ('lightning-strike-amazon', "Bul-Kathos' Wedding Band", 'Rings'),
    ('meteor-sorceress', 'Goldwrap', 'Belts'),
    ('mirrored-blades-warlock-guide', 'Stealth', 'Body Armors'),
    ('nova-sorceress-guide', "Tal Rasha's Fine-Spun Cloth", 'Belts'),
    ('poison-nova-necromancer', 'Bramble', 'Body Armor'),
    ('smite-paladin', 'Fleshripper', 'Weapon'),
    ('strafe-amazon', 'Gore Rider', 'Boots'),
    ('summoner-necromancer-guide', 'Splendor', 'Off-Hand'),
    ('wake-of-fire-assassin', "Bartuc's Cut-Throat", 'Weapon'),
}


def test_plain_player_table_links_across_builds_retain_slot_context():
    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    bundle = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    rows = compile_table_equivalence(doc, inventory['occurrences'], bundle['profiles'], uses, Path.cwd())
    occurrences = {o['id']: o for o in inventory['occurrences']}
    linked = {
        (o['build'], o['name'], o['slot'])
        for row in rows
        if (o := occurrences[row['occurrence_id']])['side'] == 'player'
    }
    assert linked >= EXPECTED


def test_table_family_never_duplicates_a_dedicated_source_context_review():
    tables = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())['rows']
    contexts = json.loads(Path('pricing/knowledge/assessment/rules/source_context_reviews.json').read_text())['rows']
    assert {r['occurrence_id'] for r in tables}.isdisjoint(r['occurrence_id'] for r in contexts)
