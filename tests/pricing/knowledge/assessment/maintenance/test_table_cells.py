import pytest

from pricing.knowledge.assessment.maintenance.table_cells import CellMentions, require_early_armor_cell


ITEM = '<span class="d2planner-item" data-d2planner-profile="fc01065b" data-d2planner-id="93">Gemmed Dusk Shroud</span>'


def parse(body):
    parser = CellMentions()
    parser.feed(body)
    parser.close()
    return parser


def table(first='Early-Game', row='Body Armor', early=ITEM, middle='Smoke'):
    return (
        f'<table><tr><th>Gear Level</th><th>{first}</th><th>Mid-Game</th></tr>'
        f'<tr><td>{row}</td><td>{early}</td><td>{middle}</td></tr></table>'
    )


def test_repeated_item_labels_keep_their_actual_table_cells():
    parser = parse(table(middle=ITEM))
    require_early_armor_cell(parser, 0)
    with pytest.raises(ValueError, match='early body armor'):
        require_early_armor_cell(parser, 1)


@pytest.mark.parametrize(
    'body', [ITEM, table(first='End-Game'), table(row='Helmet'), table(early='Smoke', middle=ITEM)]
)
def test_unrelated_or_wrong_progression_cells_are_rejected(body):
    with pytest.raises(ValueError, match='early body armor'):
        require_early_armor_cell(parse(body), 0)


def test_tables_do_not_borrow_each_others_headers():
    parser = parse(table() + table(first='End-Game'))
    require_early_armor_cell(parser, 0)
    with pytest.raises(ValueError, match='early body armor'):
        require_early_armor_cell(parser, 1)


def test_spanning_cells_require_an_explicit_layout_review():
    body = table().replace('<td>Body Armor', '<td rowspan="2">Body Armor')
    with pytest.raises(ValueError, match='early body armor'):
        require_early_armor_cell(parse(body), 0)
