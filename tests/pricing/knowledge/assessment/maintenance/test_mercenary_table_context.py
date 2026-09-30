import pytest

from pricing.knowledge.assessment.maintenance.mercenary_table_context import validate_table_context


def test_adjacent_explicit_might_context_supports_table():
    sections = [
        {'heading': 'Insight, Might', 'text': 'Use a Desert Mercenary with Might Aura. Equip him with Insight.'},
        {'heading': 'Gear Progression', 'text': 'Slot Early-Game Mid-Game End-Game Weapon Insight'},
    ]
    assert validate_table_context(sections, 1, sections[0]['text']) is None


@pytest.mark.parametrize('change', ['player', 'nonadjacent', 'wrong_table', 'partial_quote'])
def test_unrelated_wearer_or_table_cannot_reassign_player_items(change):
    sections = [
        {'heading': 'Insight, Might', 'text': 'Use a Desert Mercenary with Might Aura. Equip him with Insight.'},
        {'heading': 'Gear Progression', 'text': 'Slot Early-Game Mid-Game End-Game Weapon Insight'},
    ]
    quote = sections[0]['text']
    if change == 'player':
        sections[0]['text'] = quote = 'Equip your character with Insight.'
    elif change == 'nonadjacent':
        sections.insert(1, {'heading': 'Other', 'text': 'Unrelated'})
    elif change == 'wrong_table':
        sections[1]['heading'] = 'Player Gear'
    else:
        quote = 'Use a Desert Mercenary with Might Aura.'
    with pytest.raises(ValueError, match='mercenary table'):
        validate_table_context(sections, len(sections) - 1, quote)
