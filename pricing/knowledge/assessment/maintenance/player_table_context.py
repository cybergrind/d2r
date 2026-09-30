"""Validate table placement independently of the legacy item extractor's side label."""

from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions


class TableMentions(PositionedMentions):
    def __init__(self):
        super().__init__()
        self.table_depth = 0
        self.table_membership = []
        self.active_table = False
        self.entry_labels = {}
        self.entry_ends = {}
        self.entry_chunks = {}

    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'td', 'th', 'tr', 'table'):
            self.finish_entries()
        if tag == 'table':
            self.table_depth += 1
        active = self.active
        super().handle_starttag(tag, attrs)
        if active is None and self.active is not None:
            self.active_table = self.table_depth > 0
            self.entry_chunks[len(self.mentions)] = []

    def handle_data(self, data):
        super().handle_data(data)
        for chunks in self.entry_chunks.values():
            chunks.append(data)

    def finish_entries(self):
        for index, chunks in self.entry_chunks.items():
            self.entry_labels[index] = ' '.join(' '.join(chunks).split())
            self.entry_ends[index] = self.getpos()
        self.entry_chunks.clear()

    def close(self):
        super().close()
        self.finish_entries()

    def handle_endtag(self, tag):
        if tag in ('td', 'th', 'tr', 'table'):
            self.finish_entries()
        count = len(self.mentions)
        super().handle_endtag(tag)
        if len(self.mentions) > count:
            self.table_membership.append(self.active_table)
        if tag == 'table':
            self.table_depth = max(0, self.table_depth - 1)


def require_player_table(parser, sections, index):
    enclosing = [s for s in sections if tuple(s['position']) < parser.positions[index]]
    if not parser.table_membership[index] or not enclosing or enclosing[-1]['heading'].casefold() != 'gear options':
        raise ValueError('Table equivalence requires a player Gear Options table')
