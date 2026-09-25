from pricing.knowledge.assessment.maintenance.set_relationships import set_relationships


DEFINITIONS = [
    {'rarity': 'set', 'name': 'Piece A', 'set_name': 'Example Set', 'table_id': 1},
    {'rarity': 'set', 'name': 'Piece B', 'set_name': 'Example Set', 'table_id': 2},
]


def test_full_set_expands_pieces_with_conditional_relationship_not_endorsement():
    row = {
        'id': 'occurrence',
        'original_label': 'Example Set full set: Piece A, Piece B',
        'source_id': 'source',
        'source_locator': '/slot/0',
    }
    links = set_relationships([row], DEFINITIONS)
    assert len(links) == 1
    assert links[0]['relationship'] == 'full_set_candidate'
    assert links[0]['pieces'] == [{'name': 'Piece A', 'table_id': 1}, {'name': 'Piece B', 'table_id': 2}]
    assert links[0]['standalone_endorsement'] is False
    assert links[0]['review_state'] == 'pending'
    assert row['original_label'] == 'Example Set full set: Piece A, Piece B'


def test_piece_membership_and_partial_set_do_not_require_every_piece():
    rows = [
        {'id': 'piece', 'name': 'Piece A', 'original_label': 'Piece A (2-Piece Set)'},
        {'id': 'mention', 'original_label': 'Example Set alternative'},
        {'id': 'substring', 'original_label': 'NotExample Setish'},
    ]
    links = set_relationships(rows, DEFINITIONS)
    assert [(r['occurrence_id'], r['relationship']) for r in links] == [
        ('mention', 'set_reference_candidate'),
        ('piece', 'piece_membership'),
    ]
    assert all(r['required_piece_ids'] is None for r in links)
