"""Display attainable named socket rolls while retaining captured contents."""

from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.named_sockets import native_socket_roll, socket_gaps, socket_outcomes


def display_socket_ranges(extraction, rows):
    candidates = [r for r in rows if r.get('memory_stat', {}).get('id') == 194]
    if len(candidates) != 1:
        return rows
    facts = normalize(extraction)
    if facts.identified is not True:
        return rows
    definition, errors = resolve_named_definition(facts)
    if errors or definition is None or native_socket_roll(definition) is None:
        return rows
    original = candidates[0]
    if original.get('status') != 'decoded' or type(original.get('value')) is not int:
        return rows
    row = {k: v for k, v in original.items() if not k.startswith('roll_')}
    _, separator, contents = original.get('text', '').partition(' — ')
    row['text'] = f'Sockets: {row["value"]}'
    possible, errors = socket_outcomes(definition, facts.item_level)
    if not errors and possible and not socket_gaps(facts, definition):
        annotate_roll_ranges(
            [row],
            {
                'roll_ranges': {
                    '194': {'stat_id': 194, 'min': min(possible), 'max': max(possible), 'better': 'higher'}
                },
                'source': definition['source'],
                'scope': 'native socket outcomes after original base and item-level caps',
            },
        )
    row['text'] += separator + contents
    return [row if r is original else r for r in rows]
