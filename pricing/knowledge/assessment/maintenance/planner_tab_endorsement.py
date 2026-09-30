"""Bind a named guide tab to its text and embedded planner profile."""

from html.parser import HTMLParser


class TabParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.group = None
        self.capture = None
        self.groups = []
        self.hidden = None
        self.invalid = False

    def handle_starttag(self, tag, attrs):
        if self.hidden:
            return
        if tag in ('script', 'style'):
            self.hidden = tag
            return
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()
        if tag == 'div':
            self.depth += 1
            if any(c.startswith('_tabsV2_') for c in classes):
                if self.group is not None:
                    self.invalid = True
                    return
                self.group = {'depth': self.depth, 'headers': [], 'tabs': []}
            elif self.group and any(c.startswith(('_header_', '_tab_')) for c in classes):
                if self.capture is not None:
                    self.invalid = True
                    return
                kind = 'headers' if any(c.startswith('_header_') for c in classes) else 'tabs'
                self.capture = {'depth': self.depth, 'parts': [], 'planners': []}
                self.group[kind].append(self.capture)
        if self.capture:
            if tag in ('p', 'div', 'br', 'li', 'h2', 'h3', 'h4'):
                self.capture['parts'].append(' ')
            if 'd2-player' in classes:
                self.capture['planners'].append((attributes.get('data-d2-id'), attributes.get('data-d2-set-id')))

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden:
                self.hidden = None
            return
        if self.capture and tag in ('p', 'div', 'li', 'h2', 'h3', 'h4'):
            self.capture['parts'].append(' ')
        if tag == 'div':
            if self.capture and self.capture['depth'] == self.depth:
                self.capture = None
            if self.group and self.group['depth'] == self.depth:
                self.groups.append(self.group)
                self.group = None
            self.depth -= 1

    def handle_data(self, text):
        if self.capture and not self.hidden:
            self.capture['parts'].append(text)


def normalized(parts):
    return ' '.join(''.join(parts).split())


def selected_tab(html, label, planner_id, profile_uid):
    parser = TabParser()
    parser.feed(html)
    parser.close()
    if (
        parser.invalid
        or parser.group
        or not all(isinstance(v, str) and v.strip() for v in (label, planner_id, profile_uid))
    ):
        return None
    matches = []
    for group in parser.groups:
        if len(group['headers']) != len(group['tabs']):
            continue
        for header, tab in zip(group['headers'], group['tabs'], strict=True):
            if normalized(header['parts']).casefold() == label.casefold():
                matches.append(tab)
    if len(matches) != 1 or (planner_id, profile_uid) not in matches[0]['planners']:
        return None
    return matches[0]


def tab_selects_equipment(html, label, planner_id, profile_uid):
    return selected_tab(html, label, planner_id, profile_uid) is not None


def tab_endorses(html, label, planner_id, profile_uid, quote):
    tab = selected_tab(html, label, planner_id, profile_uid)
    return bool(tab is not None and isinstance(quote, str) and quote.strip() and quote in normalized(tab['parts']))
