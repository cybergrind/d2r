from inventory_tracking.osd.demo import resource_frame
from inventory_tracking.osd.presenter import Presenter


def test_resource_preview_sequence():
    presenter = Presenter()
    expected = [
        [],
        ['tele 18/20 repair', 'tp: 17'],
        ['tele 3/20'],
        ['tele 0/20'],
        ['tele 10/20 repair', 'tp: 17'],
        [],
    ]
    for index, lines in enumerate(expected):
        now = 100 + index * 3
        presenter.update(resource_frame(now=now, elapsed=index * 3))
        assert presenter.render(now=now) == lines


def test_repair_preview_shows_the_text_reminder_and_one_mark():
    from inventory_tracking.osd.demo import repair_frame

    presenter = Presenter()
    presenter.update(repair_frame(now=100))
    assert presenter.render(now=100) == ['tele 10/20 repair']
    assert [mark.kind for mark in presenter.marks(now=100)] == ['repair']
