"""Corpus: distinct captured items, a stable labelling sample and the label score."""

import json

from inventory_tracking.corpus.build import collect, item_id, label_page, sample
from inventory_tracking.corpus.score import score


def observation(name, rarity='unique', stats=('Defense: 59',), **item):
    return {
        'item': {'name': name, 'rarity': rarity, **item},
        'decoded_stats': [{'status': 'decoded', 'text': text} for text in stats],
    }


def test_repeated_captures_of_one_item_collapse_and_rolls_keep_items_apart(tmp_path):
    captures = [observation('Magefist'), observation('Magefist'), observation('Magefist', stats=('Defense: 71',))]
    for index, capture in enumerate(captures):
        request = tmp_path / 'run' / f'request-{index}'
        request.mkdir(parents=True)
        (request / 'frozen.json').write_text(json.dumps({'observation': capture}))
    (tmp_path / 'run' / 'request-9').mkdir()
    (tmp_path / 'run' / 'request-9' / 'frozen.json').write_text('{"selection": {}}')  # rejected request
    assert len(collect(tmp_path)) == 2


def test_sample_is_stable_and_prefers_distinct_names():
    items = {}
    for index in range(60):
        capture = observation('Ring' if index < 50 else f'Unique {index}', stats=(f'+{index} to Life',))
        items[item_id(capture)] = capture
    chosen = sample(items)
    assert chosen == sample(items)
    assert len(chosen) == 45
    assert {items[i]['item']['name'] for i in chosen} >= {f'Unique {index}' for index in range(50, 60)}


def test_label_page_escapes_item_text_and_lists_every_sampled_item():
    capture = observation('<b>Ring</b>', rarity='rare', ethereal=True)
    page = label_page({'abc': capture}, ['abc'])
    assert '<section id="abc"' in page
    assert '&lt;b&gt;Ring&lt;/b&gt;' in page
    assert 'rare · ethereal' in page


def test_score_counts_missed_valuables_and_unwanted_keeps():
    results = [
        {'id': 'a', 'name': 'Magefist', 'rarity': 'unique', 'verdict': 'keep', 'reason': 'x', 'estimate_ist': 2.5},
        {
            'id': 'b',
            'name': 'Ring',
            'rarity': 'rare',
            'verdict': 'vendor',
            'reason': 'no build use',
            'estimate_ist': None,
        },
        {
            'id': 'c',
            'name': "Sigon's Gage",
            'rarity': 'set',
            'verdict': 'keep',
            'reason': 'build demand',
            'estimate_ist': None,
        },
        {'id': 'd', 'name': 'Unlabelled', 'rarity': 'magic', 'verdict': 'keep', 'reason': 'x', 'estimate_ist': None},
    ]
    summary = score(results, {'a': 'sell', 'b': 'slow', 'c': 'vendor'}, legacy=True)
    assert (summary['labelled'], summary['worth'], summary['keeps'], summary['priced']) == (3, 2, 2, 1)
    assert summary['recall'] == 0.5
    assert summary['precision'] == 0.5
    assert summary['missed'] == ['Ring (rare): no build use']
    assert summary['false_keeps'] == ["Sigon's Gage (set): build demand"]


def test_triage_score_separates_liquid_precision_trade_recall_and_sell_band_coverage():
    results = [
        {'id': key, 'name': key, 'rarity': 'magic', 'reason': 'test', 'verdict': verdict, 'band': band}
        for key, verdict, band in (
            ('a', 'sell', {'median_ist': 1}),
            ('b', 'slow', None),
            ('c', 'sell', {'median_ist': 0.5}),
            ('d', 'self', None),
            ('e', 'sell', None),
        )
    ]
    summary = score(results, {'a': 'sell', 'b': 'sell', 'c': 'slow', 'd': 'sell', 'e': 'vendor'})
    assert summary['recall'] == 0.75
    assert summary['precision'] == 0.333  # Slow demand is not a correct liquid SELL.
    assert summary['sell_band_coverage'] == 0.333  # Only a out of the three sell-labelled items.
    assert summary['missed'] == ['d (magic): test']
    assert summary['false_keeps'] == ['c (magic): test', 'e (magic): test']


def test_unlabelled_corpus_does_not_manufacture_zero_scores():
    summary = score([], {})
    assert summary['recall'] is None
    assert summary['precision'] is None
    assert summary['sell_band_coverage'] is None


def test_corpus_collects_full_auto_identified_observations(tmp_path):
    capture = observation('Rare Ring', rarity='rare')
    directory = tmp_path / 'run' / 'identified'
    directory.mkdir(parents=True)
    (directory / 'drop.json').write_text(json.dumps({'observation': capture}))
    assert collect(tmp_path) == {item_id(capture): capture}


def test_saved_triage_scoring_never_invokes_the_detail_engine(tmp_path, monkeypatch, capsys):
    from inventory_tracking.corpus import score as scorer

    (tmp_path / 'items.jsonl').write_text('')
    (tmp_path / 'labels.json').write_text(json.dumps({'a': 'sell'}))
    results = tmp_path / 'results.json'
    results.write_text(
        json.dumps(
            [
                {
                    'id': 'a',
                    'name': 'Rune',
                    'rarity': 'normal',
                    'verdict': 'sell',
                    'reason': 'band',
                    'band': {'median_ist': 0.25},
                }
            ]
        )
    )

    def forbidden(*args, **kwargs):
        raise AssertionError('Detail engine must not run during triage scoring')

    monkeypatch.setattr(scorer, 'assess_all', forbidden)
    scorer.main(['--data', str(tmp_path), '--results', str(results)])
    output = capsys.readouterr().out
    assert '1 items assessed; 1 with a price' in output
    assert '"sell_band_coverage": 1.0' in output
