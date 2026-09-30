"""Exact source interval for Hardcore-only advice, shared by text and tooltips."""


def validate_hardcore_bounds(sections, bounds, position):
    start, stop = bounds['start'], bounds['stop']
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop < len(sections):
        raise ValueError('Invalid Hardcore section bounds')
    first, last = sections[start], sections[stop]
    if last['heading'] not in {'Summary', 'Mechanics'} or any(
        section['heading'] in {'Summary', 'Mechanics', 'Standard', 'Softcore', 'Hardcore'}
        for section in sections[start + 1 : stop]
    ):
        raise ValueError('Unsupported Hardcore section boundary')
    quote = bounds.get('quote')
    if (
        first['heading'] != 'Hardcore'
        or bounds.get('start_heading') != first['heading']
        or bounds.get('stop_heading') != last['heading']
        or not isinstance(quote, str)
        or not quote.strip()
        or quote not in first['text']
        or 'Hardcore' not in quote
    ):
        raise ValueError('Unsupported Hardcore section rationale')
    if not tuple(first['position']) < tuple(position) < tuple(last['position']):
        raise ValueError('Occurrence is outside reviewed Hardcore section')
