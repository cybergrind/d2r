"""Single-sample formatting compatibility; live consumers retain a Presenter."""

from ..config import OSD
from .presenter import Presenter


def display_lines(state, *, now, config=OSD):
    presenter = Presenter(config)
    presenter.update(state)
    return presenter.render(now=now)
