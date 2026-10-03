import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.enhanced_defense import capture_gap
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('name', 'ed', 'defense', 'family'),
    [
        ('Vampire Gaze', 100, 378, 'helm'),
        ('Shaftstop', 200, 963, 'armor'),
        ('Guardian Angel', 187, 1182, 'armor'),
        ("The Gladiator's Bane", 150, 1857, 'armor'),
        ("The Gladiator's Bane", 200, 2219, 'armor'),
    ],
)
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_ethereal_base_is_scaled_before_percent_enhancement(name, ed, defense, family, offset):
    definition = catalog().named['unique', name]
    item = Item(
        definition['base_definition']['name'],
        'unique',
        name,
        ((16, 0, ed), (31, 0, defense + offset)),
        ethereal=True,
        complete=True,
    )
    assert (capture_gap(normalize(item.capture()), definition, family) is None) is (offset == 0)


def test_ethereal_upgrade_remains_explicitly_outside_this_original_base_proof():
    definition = catalog().named['unique', 'Guardian Angel']
    item = Item(
        'Hellforge Plate', 'unique', 'Guardian Angel', ((16, 0, 187), (31, 0, 1700)), ethereal=True, complete=True
    )
    assert capture_gap(normalize(item.capture()), definition, 'armor') is None


@pytest.mark.parametrize(('ethereal', 'defense'), [(False, 252), (True, 378)])
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_complete_vampire_gaze_contract_checks_total_defense(monkeypatch, ethereal, defense, offset):
    import pricing.knowledge.assessment.handlers.named as candidate_named

    monkeypatch.setattr(candidate_named, 'enhanced_defense_gap', capture_gap)
    item = Item(
        'Grim Helm',
        'unique',
        'Vampire Gaze',
        (
            (62, 0, 8),
            (60, 0, 8),
            (154, 0, 15),
            (36, 0, 20),
            (35, 0, 15),
            (16, 0, 100),
            (54, 0, 6),
            (55, 0, 22),
            (56, 0, 100),
            (31, 0, defense + offset),
        ),
        ethereal=ethereal,
        complete=True,
    )
    contract, gaps = candidate_named.NamedHandler().contract(normalize(item.capture()), 'helm')
    assert (contract is not None) is (offset == 0), gaps
