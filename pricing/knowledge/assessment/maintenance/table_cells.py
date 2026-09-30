"""Retain real table coordinates for source links with progression-column semantics."""

from pricing.knowledge.assessment.maintenance.player_table_context import TableMentions


class CellMentions(TableMentions):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.table_count = 0
        self.cells = {}
        self.locations = []
        self.complex_tables = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.frames.append({'table': self.table_count, 'row': -1, 'cell': -1, 'chunks': None})
            self.table_count += 1
        elif self.frames:
            frame = self.frames[-1]
            if tag == 'tr':
                frame['row'] += 1
                frame['cell'] = -1
            elif tag in ('td', 'th'):
                if any(k in ('colspan', 'rowspan') and v != '1' for k, v in attrs):
                    self.complex_tables.add(frame['table'])
                frame['cell'] += 1
                frame['chunks'] = []
        super().handle_starttag(tag, attrs)

    def handle_data(self, data):
        for frame in self.frames:
            if frame['chunks'] is not None:
                frame['chunks'].append(data)
        super().handle_data(data)

    def handle_endtag(self, tag):
        before = len(self.mentions)
        super().handle_endtag(tag)
        location = None
        if self.frames:
            frame = self.frames[-1]
            if frame['chunks'] is not None:
                location = (frame['table'], frame['row'], frame['cell'])
            if tag in ('td', 'th') and location is not None:
                self.cells[location] = ' '.join(' '.join(frame['chunks']).split())
                frame['chunks'] = None
        self.locations.extend([location] * (len(self.mentions) - before))
        if tag == 'table' and self.frames:
            self.frames.pop()


def require_early_armor_cell(parser, index):
    location = parser.locations[index] if 0 <= index < len(parser.locations) else None
    if location is not None:
        table, row, cell = location
        if (
            table not in parser.complex_tables
            and cell == 1
            and row > 0
            and parser.cells.get((table, 0, 0)) in ('Gear Level', 'Slot')
            and parser.cells.get((table, 0, 1)) == 'Early-Game'
            and parser.cells.get((table, row, 0)) == 'Body Armor'
        ):
            return
    raise ValueError('Source mention is not in the early body armor cell')
