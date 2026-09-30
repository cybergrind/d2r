"""A narrow wearer correction for a table immediately following Might instructions."""


def validate_table_context(sections, index, wearer_quote):
    if not 0 < index < len(sections):
        raise ValueError('Invalid mercenary table section')
    previous, table = sections[index - 1], sections[index]
    if (
        previous.get('text') != wearer_quote
        or 'Use a Desert Mercenary with Might Aura' not in wearer_quote
        or 'Equip him with ' not in wearer_quote
        or table.get('heading') != 'Gear Progression'
        or not table.get('text', '').startswith('Slot Early-Game Mid-Game End-Game ')
    ):
        raise ValueError('Unsupported mercenary table wearer context')
