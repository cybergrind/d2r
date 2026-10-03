"""Resolve ambiguous guide rows against their explicitly linked planner examples."""

import hashlib
import json


PLANNER = 'pricing/raw/mr/planners/qx0106eh.json'


def linked_rows(guide_html):
    from pricing.knowledge.valuable import GuideTable

    class LinkedRows(GuideTable):
        def __init__(self):
            super().__init__()
            self.links = {}

        def handle_starttag(self, tag, attrs):
            super().handle_starttag(tag, attrs)
            attrs = dict(attrs)
            if self.row is not None and 'data-d2planner-id' in attrs:
                self.links.setdefault(len(self.rows), set()).add(
                    (attrs.get('data-d2planner-profile'), attrs['data-d2planner-id'])
                )

    guide = LinkedRows()
    guide.feed(guide_html)
    return guide


def planner_specs(read, guide_html):
    guide = linked_rows(guide_html)
    raw = read(PLANNER)
    document = json.loads(raw)
    if document.get('id') != 'qx0106eh':
        raise ValueError('Plain resistance planner identity changed')
    items = json.loads(document['data'])['items']
    specs, sources = [], {}
    for ident, resistance, tier in (('101', 5, 'High'), ('102', 4, 'Medium'), ('127', 3, 'Low')):
        item = items[ident]
        expected = dict.fromkeys(('fireresist', 'lightresist', 'coldresist', 'poisonresist'), resistance)
        matches = [i for i, links in guide.links.items() if links == {('qx0106eh', ident)}]
        if (
            len(matches) != 1
            or guide.rows[matches[0]][:2] != ['Shimmering Small Charm', tier]
            or '0-9 Life' not in guide.rows[matches[0]][2]
            or item.get('mods') != {'mp322': [resistance]}
            or item.get('stats') != expected
            or item.get('quality') != 3
            or item.get('ethereal') is not False
            or item.get('sockets') != 0
        ):
            raise ValueError(f'Plain resistance guide/planner evidence changed: {ident}')
        # Base is verified against the existing native affix applicability in
        # collectible_watches; the planner must also identify that native base.
        misc = json.loads(read('third-parties/d2data/json/misc.json'))
        bases = [r['code'] for r in misc.values() if r.get('name') == 'Small Charm']
        if bases != [item.get('base')]:
            raise ValueError('Plain resistance planner base changed')
        key = f'plain-res-{resistance}'
        specs.append(
            (
                key,
                'Small Charm',
                'Shimmering Small Charm',
                '0-9 Life',
                {**{f'{s}:0': (resistance, resistance) for s in (39, 41, 43, 45)}, '7:0': (0, 9)},
                (),
                f'All resistances: {resistance}; 0-9 life (guide priority: {tier.lower()})',
                tier,
            )
        )
        sources[key] = {
            'path': PLANNER,
            'sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'locator': f'data/items/{ident}',
            'source_date': document['date'],
        }
    return specs, sources
