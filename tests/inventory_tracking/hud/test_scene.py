"""Scene protocol: one lease file per producer, merged by the renderer."""

import json

from inventory_tracking.hud.scene import LEASE_SECONDS, Widget, publish_layer, read_scene


GUIDE = Widget('guide', 'guide', 'guide', {'lines': [], 'map': None})


def test_layers_merge_in_producer_then_id_order(tmp_path):
    publish_layer(tmp_path, 'levels', [GUIDE], now=100.0)
    publish_layer(tmp_path, 'appraisal', [Widget('card', 'text', 'assessment', {'lines': ['Ring']})], now=100.0)

    scene = read_scene(tmp_path, now=100.5)

    assert [(w.id, w.slot) for w in scene] == [('card', 'assessment'), ('guide', 'guide')]
    assert scene[1] == GUIDE


def test_stale_or_cleared_layer_disappears(tmp_path):
    publish_layer(tmp_path, 'levels', [GUIDE], now=100.0)

    assert read_scene(tmp_path, now=100.0 + LEASE_SECONDS + 0.1) == []
    publish_layer(tmp_path, 'levels', [], now=101.0)
    assert read_scene(tmp_path, now=101.0) == []


def test_malformed_files_are_ignored_not_fatal(tmp_path):
    publish_layer(tmp_path, 'levels', [GUIDE], now=100.0)
    (tmp_path / 'broken.json').write_text('{not json')
    (tmp_path / 'wrong.json').write_text(json.dumps({'checked_at': 100.0, 'widgets': [{'id': 1}]}))

    assert read_scene(tmp_path, now=100.1) == [GUIDE]


def test_missing_directory_is_an_empty_scene(tmp_path):
    assert read_scene(tmp_path / 'absent', now=0.0) == []
