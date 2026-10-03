"""Bind an explicit ordinary-use review to its exact early mercenary table cell.

This validates reviewed evidence; it never chooses which items are valuable or
creates exclusions from a column label alone.
"""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.guide_sections import SectionParser, section_inventory


class GearTables(SectionParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = self.item = None
        self.nested_tables = 0
        self.span_depth = 0
        self.item_depth = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if self.hidden:
            return
        if self.nested_tables:
            if tag == 'table':
                self.nested_tables += 1
            return
        attributes = dict(attrs)
        if tag == 'table':
            if self.table is not None:
                self.table['unsupported'] = True
                self.nested_tables = 1
                return
            self.table = {'section_locator': self.sections[-1]['locator'], 'rows': []}
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            if any(attributes.get(key, '1') != '1' for key in ('rowspan', 'colspan')):
                self.table['unsupported'] = True
            self.cell = {'parts': [], 'items': []}
        elif tag == 'br' and self.cell is not None:
            self.cell['parts'].append(' ')
        if tag == 'span':
            self.span_depth += 1
            if self.cell is not None and 'd2planner-item' in attributes.get('class', '').split():
                if self.item is not None:
                    raise ValueError('Nested item labels are unsupported')
                self.item = []
                self.item_depth = self.span_depth

    def handle_data(self, data):
        super().handle_data(data)
        if self.hidden or self.nested_tables:
            return
        if self.cell is not None:
            self.cell['parts'].append(data)
        if self.item is not None:
            self.item.append(data)

    def handle_endtag(self, tag):
        hidden = self.hidden
        super().handle_endtag(tag)
        if hidden:
            return
        if self.nested_tables:
            if tag == 'table':
                self.nested_tables -= 1
            return
        if tag == 'span':
            if self.item is not None and self.span_depth == self.item_depth:
                self.cell['items'].append(' '.join(''.join(self.item).split()))
                self.item = self.item_depth = None
            self.span_depth -= 1
        elif tag in ('td', 'th') and self.cell is not None:
            self.cell['text'] = ' '.join(''.join(self.cell.pop('parts')).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table['rows'].append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def validate_table_context(row, profile, root):
    from pricing.knowledge.assessment.maintenance.value_scope import json_value

    context = row['table_context']
    expected = {'path', 'sha256', 'section_locator', 'table_index', 'row_index', 'column_index'}
    if not isinstance(context, dict) or set(context) != expected:
        raise ValueError('Invalid early mercenary table context')
    if (
        row['classification'] != 'generic_leveling'
        or profile.get('side') != 'merc'
        or profile.get('variant') != 'Gear alternatives'
        or profile.get('names') != [row['quote']]
        or context['path'] != f'pricing/raw/mr/guides__{profile.get("build")}.html'
        or any(type(context[k]) is not int or context[k] < 0 for k in ('table_index', 'row_index', 'column_index'))
    ):
        raise ValueError('Table review does not address this exact mercenary use')
    try:
        date.fromisoformat(row.get('reviewed_at', ''))
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid early mercenary review date') from exc
    path = (root / context['path']).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing local mercenary guide')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != context['sha256']:
        raise ValueError('Changed mercenary guide')
    source = profile['source']
    prefix = '/sources/' + context['path'].replace('~', '~0').replace('/', '~1')
    if (
        source['path'] != 'pricing/data/appraisal-guide-sections.json'
        or source['locator'] != prefix + context['section_locator']
    ):
        raise ValueError('Table context is not the profile source section')
    document = json.loads((root / source['path']).read_bytes())
    guide = document['sources'][context['path']]
    section = json_value(guide, context['section_locator'])
    html = raw.decode()
    actual_section = json_value(section_inventory(html), context['section_locator'])
    if (
        guide['source_sha256'] != context['sha256']
        or section['heading'] != 'Mercenary Gear Options'
        or any(section[k] != actual_section[k] for k in ('locator', 'heading', 'position', 'text'))
    ):
        raise ValueError('Cached section disagrees with raw mercenary guide')
    parser = GearTables()
    parser.feed(html)
    parser.close()
    try:
        table = parser.tables[context['table_index']]
        headers = table['rows'][0]
        cells = table['rows'][context['row_index']]
        column = context['column_index']
        valid = (
            not table.get('unsupported')
            and table['section_locator'] == context['section_locator']
            and len(headers) == 4
            and headers[0]['text'] in ('Slot', 'Gear Level')
            and [c['text'] for c in headers[1:]] == ['Early-Game', 'Mid-Game', 'End-Game']
            and len(cells) == len(headers)
            and context['row_index'] > 0
            and column == 1
            and cells[0]['text'] == profile['slot']
            and row['quote'] in cells[column]['items']
        )
    except IndexError, KeyError:
        valid = False
    if not valid:
        raise ValueError('Item is not in the reviewed early mercenary gear cell')
