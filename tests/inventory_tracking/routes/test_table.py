"""The route tables of levels/routes.md are the catalogue's, not a copy kept by hand."""

from inventory_tracking.routes import table
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import Route, enter, leave, level, loot, use


def test_a_route_is_a_row_of_its_start_and_its_levels_stages():
    route = Route(
        'Hole',
        (6,),
        (
            level(6, enter('Hole 1', 11), alternate=True),
            level(11, enter('Next level', 15)),
            level(15, use('Super chest', pending='no click yet'), loot(), leave()),
        ),
    )

    assert table.row(route) == (
        '| Hole | Black Marsh | *Black Marsh*: enter Hole 1<br>Hole 1: enter Next level<br>'
        'Hole 2: use Super chest (pending) → loot → leave |'
    )
    assert '| Hole | Hole 2 | use Super chest (pending) | no click yet |' in table.render([route])


def test_the_tables_go_between_the_documents_markers_and_leave_the_rest():
    document = f'before\n{table.BEGIN}\nold\n{table.END}\nafter\n'

    assert table.embedded(document) == 'old'
    assert table.embed(document, 'new') == f'before\n{table.BEGIN}\nnew\n{table.END}\nafter\n'


def test_routes_md_holds_the_tables_of_the_catalogue():
    # After a catalogue change: uv run --offline python -m inventory_tracking.routes --write
    assert table.embedded(table.DOCUMENT.read_text()) == table.render(ROUTES)
