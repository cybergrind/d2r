from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'tier'),
    [
        ("Ars Dul'Mephistos", 'high'),
        ("Ars Tor'Baalos", 'high'),
        ('Blade of Ali Baba', 'low'),
        ('Dreadfang', 'low'),
        ('Dwarf Star', 'low'),
        ('Entropy Locket', 'high'),
        ("Gheed's Wager", 'high'),
        ('Goldwrap', 'trash'),
        ('Lidless Wall', 'low'),
        ('Magefist', 'low'),
        ('Nagelring', 'low'),
        ('Peasant Crown', 'trash'),
        ('Silkweave', 'low'),
        ('Suicide Branch', 'low'),
        ('Tarnhelm', 'low'),
        ('The Oculus', 'low'),
        ('Wizardspike', 'trash'),
        ("Guardian's Thunder", 'high'),
        ("Protector's Stone", 'high'),
        ("Defender's Fire", 'high'),
    ],
)
def test_reviewed_unique_baseline_uses_exact_identity_and_variant_scope(name, tier):
    definition = named_definitions()['unique', name]
    base = next(b for b in metadata()['bases'].values() if b['code'] == definition['base_codes'][0])
    item = facts(base['name'], 'unique', name)
    assert assess_tier(item)['tier'] == tier
    assert assess_tier(replace(item, ethereal=True))['tier'] is None
    assert assess_tier(replace(item, socket_contents='filled'))['tier'] is None
    assert assess_tier(replace(item, base_code='unverified'))['tier'] is None


def test_floor_trade_tier_does_not_remove_peasant_crown_leveling_use():
    item = facts('War Hat', 'unique', 'Peasant Crown')
    assert assess_tier(item)['tier'] == 'trash'
    assert assess_leveling(item)
