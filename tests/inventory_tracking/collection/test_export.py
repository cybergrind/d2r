import json
import re
from html.parser import HTMLParser

from inventory_tracking.collection.export import export_html, export_payload, render_html, unresolved_text
from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location, Sighting
from inventory_tracking.collection.store import CollectionStore


def sighting(observation, character='MuleOne', *, tab=None):
    return Sighting(
        item=ItemRecord.from_observation(observation),
        location=Location.from_source(observation['source'], character, tab=tab),
    )


def embedded(text):
    match = re.search(r'<script id="data" type="application/json">(.*?)</script>', text, re.S)
    assert match
    return json.loads(match.group(1).replace('<\\/', '</'))


class Strict(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_export_embeds_every_open_placement_with_searchable_fields(tmp_path, insight, magic_ring, set_helm):
    with CollectionStore(tmp_path / 'c.sqlite') as store:
        run = CaptureRun(
            id='c1',
            character=Character(name='MuleOne', class_name='Warlock', level=9),
            containers=[('MuleOne', 'stash', None), ('MuleOne', 'inventory', None), ('shared', 'shared_stash', 2)],
            started_at='2026-09-25T10:00:00+00:00',
        )
        store.record_capture(run, [sighting(insight), sighting(magic_ring), sighting(set_helm, tab=2)])
        path = tmp_path / 'out' / 'collection.html'
        payload = export_html(store, path)
    text = path.read_text(encoding='utf-8')
    assert text.startswith('<!doctype html>')
    data = embedded(text)
    assert data == json.loads(json.dumps(payload))
    assert data['counts']['placements'] == 3
    assert data['characters'][0]['name'] == 'MuleOne'
    by_name = {r['name']: r for r in data['rows']}
    insight_row = by_name['Insight']
    assert insight_row['runeword'] == 'Insight'
    assert insight_row['sockets'] == 4
    assert insight_row['socket_items'] == ['Ral Rune', 'Tir Rune', 'Tal Rune', 'Sol Rune']
    assert '+5 to Strength' in insight_row['stats']
    assert 'sol rune' in insight_row['search']
    assert (insight_row['owner'], insight_row['where'], insight_row['x'], insight_row['y']) == (
        'MuleOne',
        'Personal stash',
        0,
        6,
    )
    helm = by_name["Tal Rasha's Horadric Crest"]
    assert helm['set'] == "Tal Rasha's Wrappings"
    assert helm['where'] == 'Shared stash 2'
    assert helm['owner'] == 'shared'
    assert by_name['Ring']['identified'] is None


def test_page_is_self_contained_and_parses(tmp_path, insight):
    with CollectionStore(tmp_path / 'c.sqlite') as store:
        run = CaptureRun(id='c1', character=Character(name='M'), containers=[('M', 'stash', None)], started_at='t')
        store.record_capture(run, [sighting(insight, 'M')])
        text = render_html(export_payload(store))
    parser = Strict()
    parser.feed(text)
    external = [a for t, a in parser.tags if t in ('script', 'link', 'img') and (a.get('src') or a.get('href'))]
    assert external == []
    assert text.count('<script') == 2
    assert 'MuleOne' not in text
    assert text.count('</script>') == 2  # data payload cannot close the script early


def test_data_payload_escapes_script_terminators():
    payload = {
        'generated_at': 't',
        'characters': [],
        'counts': {'placements': 1, 'characters': 0},
        'rows': [{'name': '</script><b>'}],
    }
    text = render_html(payload)
    assert '</script><b>' not in text.split('<script id="data"')[1].split('</script>')[0]
    assert embedded(text)['rows'][0]['name'] == '</script><b>'


def test_unresolved_text_prefers_text_then_names_the_stat():
    assert unresolved_text({'text': 'Unknown thing'}) == 'Unknown thing'
    assert (
        unresolved_text({'memory_stat': {'layer': 3, 'id': 188, 'raw': 1}, 'name': 'skilltab'})
        == 'skilltab stat 188 layer 3 = 1'
    )
    assert unresolved_text({'layer': 0, 'id': 7, 'raw': 5}) == 'stat 7 = 5'
