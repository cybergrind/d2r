"""Socket prose identifies one carrier item without consuming composite gear lists."""

import pytest

from pricing.knowledge.builds import resolve_named_label


@pytest.fixture
def catalog():
    return {
        'helm': {'name': 'Demonhead', 'category': 'armor', 'base_code': 'test-helm'},
        'shield': {'name': 'Monarch', 'category': 'armor', 'base_code': 'test-shield'},
        'jewel': {'name': 'Colossal Jewel', 'category': 'misc', 'base_code': 'test-jewel'},
        'andy': {'name': "Andariel's Visage", 'category': 'unique', 'base_code': 'test-helm'},
        'storm': {'name': 'Stormshield', 'category': 'unique', 'base_code': 'test-shield'},
        'guardian': {'name': "Guardian's Thunder", 'category': 'unique', 'base_code': 'test-jewel'},
        'topaz': {'name': 'Perfect Topaz', 'category': 'misc'},
        'set': {'name': "Sazabi's Mental Sheath", 'category': 'set', 'base_code': 'test-helm'},
        'ber': {'name': 'Ber Rune', 'category': 'misc'},
        'eld': {'name': 'Eld Rune', 'category': 'misc'},
        'cham': {'name': 'Cham Rune', 'category': 'misc'},
        'enigma': {'name': 'Enigma', 'category': 'runeword'},
    }


@pytest.mark.parametrize(
    ('label', 'key'),
    [
        ("Andariel's Visage with Ruby Jewel of Fervor (merc)", 'andy'),
        ("Andariel's Visage socketed with a Ruby Jewel of Fervor (ethereal in planner)", 'andy'),
        ('Stormshield with an Eld Rune (Hardcore)', 'storm'),
        ("Sazabi's Mental Sheath socketed with Perfect Topaz (MF)", 'set'),
        ('Stormshield socketed with Cham Rune + Ber Rune', 'storm'),
        ("Andariel's Visage socketed with Guardian's Thunder (unique Colossal Jewel)", 'andy'),
    ],
)
def test_explicit_socket_payload_resolves_only_carrier_identity(catalog, label, key):
    assert resolve_named_label(label, catalog) == catalog[key]


@pytest.mark.parametrize(
    'label',
    [
        "Andariel's Visage with Enigma",
        "Andariel's Visage with Ruby Jewel of Fervor + Enigma",
        'Stormshield with Ber Rune (socket) + Enigma',
        'Stormshield with an unknown filler',
        'Stormshield with 9x Ber Rune',
        "Guardian's Thunder with Ber Rune",
        'Rare Monarch with Ber Rune',
    ],
)
def test_other_gear_and_unverified_payload_do_not_become_one_identity(catalog, label):
    assert resolve_named_label(label, catalog) is None
