"""Bind socket filler mentions to a reviewed, intact parent item entry."""

import re
from html import unescape

from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions


BOUNDARY = re.compile(r'<(?:br\b[^>]*|/?(?:td|li|p)\b[^>]*)>', re.IGNORECASE)


def identity_matches(branch, role):
    parent = branch.get('parent_label')
    assembly = branch.get('assembly')
    return (
        isinstance(parent, str)
        and bool(parent)
        and isinstance(assembly, str)
        and assembly.startswith(parent + ' (')
        and assembly.endswith(')')
        and assembly in role['source'].get('quotes', [])
        and (parent in role.get('names', []) or (not role.get('names') and bool(role.get('types'))))
    )


def validate_entry(root, occurrence, guide, branch):
    """Do not inherit ownership from an adjacent row or a neighbouring mention."""
    parent_index = branch.get('parent_span')
    child_index = int(occurrence['source_locator'].rsplit('/', 1)[1])
    if type(parent_index) is not int or not 0 <= parent_index < child_index:
        raise ValueError('source-context socket parent must precede its filler')
    parent = guide['item_spans'][parent_index]
    if parent['label'] != branch['parent_label'] or any(
        parent.get(key) != occurrence.get(key) for key in ('side', 'slot')
    ):
        raise ValueError('source-context socket parent identity or slot changed')
    html = (root / occurrence['source_id']).read_text()
    parser = PositionedMentions()
    parser.feed(html)
    parser.close()
    lines = html.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    offsets = [starts[line - 1] + column for line, column in parser.positions]
    child_offset = offsets[child_index]
    boundaries = list(BOUNDARY.finditer(html))
    start = max((m.end() for m in boundaries if m.end() <= child_offset), default=0)
    stop = min((m.start() for m in boundaries if m.start() > child_offset), default=len(html))
    members = [index for index, offset in enumerate(offsets) if start <= offset < stop]
    text = ' '.join(unescape(re.sub(r'<[^>]*>', '', html[start:stop])).split())
    if not members or members[0] != parent_index or text != branch['assembly']:
        raise ValueError('source-context socket filler is not in the exact reviewed parent entry')
