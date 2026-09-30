"""Bind a cached item occurrence to its exact quoted HTML section."""

import hashlib

from pricing.knowledge.builds import _Mentions


class PositionedMentions(_Mentions):
    """Use the inventory's extractor semantics; add positions without changing its output."""

    def __init__(self):
        super().__init__()
        self.positions = []
        self.active_position = None

    def handle_starttag(self, tag, attrs):
        active = self.active
        super().handle_starttag(tag, attrs)
        if active is None and self.active is not None:
            self.active_position = self.getpos()

    def handle_endtag(self, tag):
        count = len(self.mentions)
        super().handle_endtag(tag)
        if len(self.mentions) > count:
            self.positions.append(self.active_position)


def require_same_section(root, occurrence, guide, evidence, positions, *, label='utility'):
    gid = occurrence['source_id']
    if gid not in positions:
        path = (root / gid).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f'Missing {label} HTML evidence')
        html = path.read_text()
        if hashlib.sha256(html.encode()).hexdigest() != guide.get('source_sha256'):
            raise ValueError(f'Stale {label} HTML evidence')
        parser = PositionedMentions()
        parser.feed(html)
        parser.close()
        if parser.mentions != guide['item_spans']:
            raise ValueError(f'{label} HTML spans disagree with the cached extraction')
        positions[gid] = parser.positions
    parts = evidence['locator'].split('/')
    if parts[-1] != 'text' or not parts[-2].isdigit():
        raise ValueError(f'{label} evidence must identify a text section')
    section_index = int(parts[-2])
    sections = guide['sections']
    start = tuple(sections[section_index]['position'])
    stop = tuple(sections[section_index + 1]['position']) if section_index + 1 < len(sections) else (float('inf'), 0)
    span_index = int(occurrence['source_locator'].rsplit('/', 1)[1])
    if not start < positions[gid][span_index] < stop:
        raise ValueError(f'{label} occurrence lies outside the quoted section')
