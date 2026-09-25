import json
from pathlib import Path

import pytest

from pricing.knowledge.utility import legal_recipe_edges, socket_options, transcript_rows


def test_recipe_legality_uses_type_ancestry_and_exact_socket_capacity():
    game = {
        'weapons': {
            'sword': {'name': 'Test Sword', 'type': 'blade', 'gemsockets': 4},
            'pole': {'name': 'Test Polearm', 'type': 'pole', 'gemsockets': 6},
        },
        'armor': {},
        'itemTypes': {'blade': {'equiv1': 'swor'}, 'swor': {}, 'pole': {}},
        'runes': {
            'spirit': {'name': 'Spirit', 'itype1': 'swor', 'rune1': 'a', 'rune2': 'b', 'rune3': 'c', 'rune4': 'd'}
        },
    }
    rows = legal_recipe_edges(game, {})
    assert [(r['name'], r['sockets']) for r in rows] == [('Test Sword', 4)]
    assert rows[0]['details']['legality'] == 'verified_type_and_capacity'


def test_unknown_ilvl_is_conditional_and_existing_sockets_cannot_be_reduced():
    base = {'gemsockets': 6, 'type': 'sword'}
    types = {'sword': {'maxsock1': 3, 'maxsock25': 4, 'maxsock40': 6}}
    result = socket_options(base, types, method='larzuk')
    assert result['conditional'] is True
    assert result['possible_sockets'] == [3, 4, 6]
    assert socket_options(base, types, method='larzuk', ilvl=28)['possible_sockets'] == [4]
    assert socket_options(base, types, method='cube', current_sockets=5)['possible_sockets'] == [5]


@pytest.mark.parametrize('quality', ['superior', 'low_quality', 'magic', 'rare', 'unique', 'set'])
def test_ordinary_cube_recipe_rejects_wrong_quality(quality):
    result = socket_options(
        {'gemsockets': 4, 'type': 'sword'},
        {'sword': {'maxsock1': 3, 'maxsock25': 4, 'maxsock40': 4}},
        method='cube',
        quality=quality,
        ilvl=30,
    )
    assert result['eligible'] is False
    assert result['possible_sockets'] == []


def test_transcript_retains_conditional_keep_and_excluded_context():
    root = Path(__file__).resolve().parents[3]
    path = root / 'pricing/data/appraisal-leveling-candidates-2026-09-23.json'
    if not path.exists():
        pytest.skip('Separate local KB snapshot is not installed')
    data = json.loads(path.read_text())
    rows, coverage = transcript_rows(data)
    hand = next(r for r in rows if r['name'] == "Death's Hand")
    assert hand['predicates']['requires_items'] == ["Death's Guard"]
    assert coverage == {'named_candidates': 70, 'patterns': 13, 'excluded_context': 4}
    assert len([r for r in rows if r['details'].get('excluded_context')]) == 4
    assert any(r['name'] == 'Pelta Lunata' and r['kind'] == 'leveling' for r in rows)


def test_guide_parser_captures_legacy_planners_and_socket_base_checklists():
    from pricing.knowledge.utility import GuideItems

    parser = GuideItems()
    parser.feed(
        '<h3 id="gear-checklist">Gear Checklist</h3><table><tr><td>2 Socket Helm</td>'
        '<td>For Lore<br>not magic</td></tr></table>'
        '<span data-d2planner-profile="example"></span>'
        '<span class="d2planner-item">Pelta Lunata</span>'
    )
    assert parser.planners == {'example'}
    assert parser.entries[0]['text'] == 'Pelta Lunata'
    assert 'not magic' in parser.checklists[0]['text']


def test_portable_corpus_covers_classes_and_does_not_confuse_legal_edges():
    from pricing.knowledge.utility import CLASSES, socket_options_from_row

    root = Path(__file__).resolve().parents[3]
    path = root / 'pricing/data/appraisal-utility.json'
    if not path.exists():
        pytest.skip('Separate local KB snapshot is not installed')
    corpus = json.loads(path.read_text())
    assert set(corpus['coverage']['classes']) == set(CLASSES)
    for covered in corpus['coverage']['classes'].values():
        assert covered['guide_item_mentions'] > 0
        assert covered['planners']
        assert all(p.get('rows', 0) > 0 for p in covered['planners'])
    assert corpus['coverage']['recipe_records'] == 99
    sources = {source['id'] for source in corpus['sources']}
    assert all(row['source_id'] in sources for row in corpus['rows'])
    edges = [row for row in corpus['rows'] if row.get('details', {}).get('legality') == 'verified_type_and_capacity']
    assert not any(
        row['name'] == 'Giant Thresher' and row['sockets'] == 6 and row['details']['runeword'] == 'Obedience'
        for row in edges
    )
    assert any(row['details']['runeword'] == 'Void' for row in edges)
    crystal = next(
        row
        for row in corpus['rows']
        if row['name'] == 'Crystal Sword' and row.get('details', {}).get('rule') == 'socket_potential'
    )
    assert socket_options_from_row(crystal, method='larzuk', ilvl=28)['possible_sockets'] == [4]
    assert socket_options_from_row(crystal, method='larzuk')['possible_sockets'] == [3, 4, 6]


def test_crafting_edges_require_empty_sockets_and_ordered_runes():
    game = {
        'weapons': {'example': {'name': 'Example', 'type': 'weapon', 'gemsockets': 2}},
        'armor': {},
        'itemTypes': {'weapon': {}},
        'runes': {'recipe': {'name': 'Example Word', 'itype1': 'weapon', 'rune1': 'first', 'rune2': 'second'}},
    }
    row = legal_recipe_edges(game, {})[0]
    assert row['predicates']['requires_empty_sockets'] is True
    assert row['predicates']['rune_order_required'] is True
    assert row['details']['rune_codes'] == ['first', 'second']
    assert row['predicates']['mode_availability_requires_verification'] is True


def test_actual_adapter_recommendations_preserve_all_crafting_prerequisites():
    from pricing.knowledge.utility import build_utility

    root = Path(__file__).resolve().parents[3]
    if (
        not (root / 'pricing/raw/mr/planners/game-data.json').exists()
        or not (root / 'pricing/data/appraisal-leveling-candidates-2026-09-23.json').exists()
    ):
        pytest.skip('Separate local KB and raw-source snapshots are not installed')
    corpus = build_utility(root)
    examples = {('Crystal Sword', 'Spirit'), ('Greater Talons', 'Mosaic'), ('Greater Talons', 'Plague')}
    seen = set()
    for row in corpus['rows']:
        if row['source_id'] != 'recommended-bases':
            continue
        predicates = row.get('predicates', {})
        assert set(predicates.get('quality', [])) == {'normal', 'superior', 'low_quality'}
        assert predicates['requires_empty_sockets'] is True
        assert predicates['rune_order_required'] is True
        assert predicates['exact_sockets'] == row['sockets']
        assert isinstance(predicates['mode_availability_requires_verification'], bool)
        assert row['details']['legality'] == 'recommendation_only'
        seen.add((row['name'], row['details']['runeword']))
    assert examples <= seen


@pytest.mark.parametrize('method', ['larzuk', 'cube', 'drop'])
def test_unknown_socket_count_does_not_become_an_unsocketed_base(method):
    result = socket_options(
        {'gemsockets': 6, 'type': 'sword'},
        {'sword': {'maxsock1': 3, 'maxsock25': 4, 'maxsock40': 6}},
        method=method,
        current_sockets=None,
        ilvl=80,
        difficulty='hell',
    )
    assert result['eligible'] is False
    assert result['conditional'] is True
    assert result['possible_sockets'] == []
    assert 'socket count' in result['reason']


@pytest.mark.parametrize(
    'record', [{}, {'maxsock1': 3, 'maxsock25': 4}, {'maxsock1': 3, 'maxsock25': 4, 'maxsock40': None}]
)
def test_missing_socket_caps_are_unverified_not_zero_socket_outcomes(record):
    result = socket_options({'gemsockets': 6, 'type': 'sword'}, {'sword': record}, method='larzuk')
    assert result['eligible'] is False
    assert result['conditional'] is True
    assert result['possible_sockets'] == []
    assert result['maximum_by_ilvl_bracket'] == []
