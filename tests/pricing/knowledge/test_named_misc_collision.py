import pytest

from pricing.knowledge.builds import resolve_named_label


@pytest.mark.parametrize(
    'label', ['Steel Grand Charm', 'Steel Grand Charm (+Attack Rating)', 'Steel Grand Charm [132 AR]']
)
def test_affixed_charms_are_not_resolved_as_runewords(label):
    catalog = {
        'steel': {'name': 'Steel', 'category': 'runeword'},
        'charm': {'name': 'Grand Charm', 'category': 'misc'},
        'sword': {'name': 'Crystal Sword', 'category': 'weapon'},
        'gheed': {'name': "Gheed's Fortune", 'category': 'unique'},
    }
    assert resolve_named_label(label, catalog) is None
    assert resolve_named_label('Steel Crystal Sword', catalog) == catalog['steel']
    assert resolve_named_label('Steel', catalog) == catalog['steel']
    assert resolve_named_label("Gheed's Fortune Grand Charm", catalog) == catalog['gheed']
