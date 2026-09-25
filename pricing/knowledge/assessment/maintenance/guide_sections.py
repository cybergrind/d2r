"""Hash-cached HTML section evidence; text presence never implies endorsement."""

import hashlib
from html import unescape
from html.parser import HTMLParser

from pricing.knowledge.builds import guide_mentions


VERSION = 'guide-sections-3'


class SectionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.embedded_item_refs = []
        self.heading_parts = None
        self.hidden = None
        self.new_section('Introduction', None, (1, 0))

    def new_section(self, heading, anchor, position):
        self.sections.append(
            {
                'locator': f'/sections/{len(self.sections)}',
                'heading': heading,
                'anchor': anchor,
                'position': list(position),
                'parts': [],
                'review_state': 'pending',
            }
        )

    def handle_starttag(self, tag, attrs):
        if self.hidden:
            return
        if tag in {'script', 'style'}:
            self.hidden = tag
            return
        attributes = dict(attrs)
        if attributes.get('data-d2-item-id'):
            self.embedded_item_refs.append(
                {
                    'profile_id': attributes.get('data-d2-id'),
                    'set_id': attributes.get('data-d2-set-id'),
                    'item_id': attributes['data-d2-item-id'],
                    'position': list(self.getpos()),
                    'section_locator': self.sections[-1]['locator'],
                }
            )
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.new_section('', dict(attrs).get('id'), self.getpos())
            self.heading_parts = []
        elif tag in {'p', 'div', 'li', 'br', 'tr', 'td', 'section'}:
            self.handle_data(' ')

    def handle_endtag(self, tag):
        if self.hidden:
            if self.hidden == tag:
                self.hidden = None
            return
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'} and self.heading_parts is not None:
            self.sections[-1]['heading'] = ' '.join(''.join(self.heading_parts).split())
            self.heading_parts = None
        elif tag in {'p', 'div', 'li', 'tr', 'td', 'section'}:
            self.handle_data(' ')

    def handle_data(self, data):
        if not self.hidden:
            target = self.heading_parts if self.heading_parts is not None else self.sections[-1]['parts']
            target.append(data)


def section_inventory(html, previous=None):
    digest = hashlib.sha256(html.encode()).hexdigest()
    if previous and previous.get('source_sha256') == digest and previous.get('extractor_version') == VERSION:
        return previous
    parser = SectionParser()
    parser.feed(html)
    parser.close()
    for section in parser.sections:
        section['text'] = ' '.join(''.join(section.pop('parts')).split())
    return {
        'source_sha256': digest,
        'item_spans': guide_mentions(unescape(html)),
        'embedded_item_refs': parser.embedded_item_refs,
        'extractor_version': VERSION,
        'sections': parser.sections,
        'complete': False,
        'scope': 'All HTML text sections except script/style; semantic relevance requires review.',
    }
