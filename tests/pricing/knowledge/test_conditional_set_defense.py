"""Dormant set ED changes original base armor at creation, not the active bonus."""

import json
from pathlib import Path

from pricing.knowledge.definitions import build_definitions
from pricing.knowledge.named_upgrades import named_upgrade_variants


ROOT = Path(__file__).resolve().parents[3]


def test_dormant_set_defense_does_not_claim_an_unmodified_base_roll():
    rows = build_definitions(ROOT)['rows']
    named = {(r['rarity'], r['name']): r for r in rows if r.get('kind') == 'item_definition'}
    # Native set generation applies partial-property functions even while their
    # stat lists are inactive. ac% fixes original armor to maxac+1: these are
    # not rolls over the ordinary white base's minac..maxac interval.
    for name in (
        "Immortal King's Detail",
        "Immortal King's Soul Cage",
        "Milabrega's Orb",
    ):
        assert named['set', name]['base_defense_range'] is None, name
    robe = named['set', "Milabrega's Robe"]
    assert robe['base_defense_range']['min'] == 234
    assert robe['base_defense_range']['max'] == 234
    bases = json.loads((ROOT / 'third-parties/d2data/json/armor.json').read_text())
    upgrades = named_upgrade_variants(robe, bases)
    assert upgrades['xar']['base_defense_range']['min'] == 417
    assert upgrades['xar']['base_defense_range']['max'] == 450
    assert upgrades['uar']['base_defense_range']['min'] == 487
    assert upgrades['uar']['base_defense_range']['max'] == 600
    assert named['unique', 'Harlequin Crest']['base_defense_range']['min'] == 98
    assert named['unique', 'Harlequin Crest']['base_defense_range']['max'] == 141
    # An ordinary partial FRW bonus leaves Horazon's random base defense intact.
    assert named['set', "Horazon's Legacy"]['base_defense_range']['min'] == 59
    assert named['set', "Horazon's Legacy"]['base_defense_range']['max'] == 68
