from inventory_tracking.osd.demo import resource_frame
from inventory_tracking.osd.presenter import Presenter


def test_resource_preview_sequence():
    presenter = Presenter()
    expected = [
        [],
        ['tele 18/20 repair', 'tp: 3'],
        ['tele 3/20', 'tp: 4'],
        ['tele 0/20', 'tp: 2'],
        ['tele 10/20 repair', 'tp: 1'],
        [],
    ]
    for index, lines in enumerate(expected):
        now = 100 + index * 3
        presenter.update(resource_frame(now=now, elapsed=index * 3))
        assert presenter.render(now=now) == lines
