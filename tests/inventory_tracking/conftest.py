from dataclasses import replace

import pytest

from inventory_tracking.models import BeltCell, BeltSnapshot, PlayerHealth, SessionIdentity, State
from inventory_tracking.native.mercenary import Mercenary


def pytest_configure(config: pytest.Config) -> None:
    # pytest-xdist registers it too; a run without the plugin (`-p no:xdist`) still knows the mark
    config.addinivalue_line('markers', 'xdist_group(name): run the tests of one group on one xdist worker')


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config: pytest.Config, log):
    """`--dist loadgroup` here is `loadfile` with groups: a test marked `xdist_group` runs with its group, any
    other test with its file (xdist's own `loadgroup` sends those one by one, so a module's cached plays and
    fixtures would be made again on every worker). The heavy arena files mark one group per cached family of
    plays, and those groups go out first, so the longest work starts at once (xdist orders the work by its
    number of tests, which puts a group of two 20-second tests last)."""
    if config.getoption('dist') != 'loadgroup':
        return None
    from xdist.scheduler import LoadGroupScheduling

    class FilesAndGroups(LoadGroupScheduling):
        groups: set[str]
        ordered = False

        def _split_scope(self, nodeid: str) -> str:
            if nodeid.rfind('@') > nodeid.rfind(']'):  # xdist appends `@group` to a marked test's id
                group = nodeid.rsplit('@', 1)[-1]
                self.groups = getattr(self, 'groups', set()) | {group}
                return group
            return nodeid.split('::', 1)[0]

        def _assign_work_unit(self, node) -> None:
            if not self.ordered:  # the first unit handed out: the work queue is complete
                self.ordered = True
                for scope in reversed([scope for scope in self.workqueue if scope in getattr(self, 'groups', ())]):
                    self.workqueue.move_to_end(scope, last=False)
            super()._assign_work_unit(node)

    return FilesAndGroups(config, log)


SESSION = SessionIdentity(1, '2', 7)
HEALING_CELLS = (BeltCell(3, 101), BeltCell(4, 102))
REJUVENATION_CELLS = (BeltCell(1, 103),)


def make_state(
    now=100,
    *,
    current_raw=500,
    maximum_raw=1000,
    belt_contents=(None,) * 16,
    healing_cells=HEALING_CELLS,
    rejuvenation_cells=REJUVENATION_CELLS,
    belt_ids=(101, 102, 103),
    **changes,
):
    """A complete, healthy, in-game sample; flat keywords fill the nested records, others replace fields."""
    return replace(
        State(
            sampled_at=now,
            session=SESSION,
            health=PlayerHealth(current_raw, maximum_raw),
            # 70%: between the merc's rejuvenation (40%) and healing (75%) thresholds, so healing is due.
            merc=Mercenary(99, 700, 1000, 22938, True),
            belt=BeltSnapshot(belt_contents, healing_cells, rejuvenation_cells, belt_ids),
        ),
        **changes,
    )


def belt_of(state: State) -> BeltSnapshot:
    assert state.belt is not None
    return state.belt


@pytest.fixture
def sample():
    return make_state


@pytest.fixture
def clock():
    class Clock:
        now = 100.0

        def __call__(self):
            return self.now

    return Clock()


@pytest.fixture
def healing_setup(tmp_path, clock):
    from unittest.mock import Mock

    from inventory_tracking.automation.heal import HealController
    from inventory_tracking.automation.ledger import PotionLedger
    from inventory_tracking.automation.potions import PotionsController

    sent = Mock()

    from tests.inventory_tracking.input.fakes import FakeDelivery

    delivery = FakeDelivery(clock=clock, on_send=sent)

    def make(config):
        return HealController(
            config, PotionsController(config, PotionLedger(tmp_path, boot_id='test'), delivery, clock=clock)
        )

    return make, sent


@pytest.fixture
def snapshot():
    def make():
        player = {
            'unit_id': 7,
            'details': {
                'full_stats': [{'layer': 0, 'id': 6, 'raw': 1526 * 256}, {'layer': 0, 'id': 7, 'raw': 1545 * 256}]
            },
        }
        items = [
            {'unit_id': i + 100, 'txt_id': 531 if i < 5 else 606, 'mode': 2, 'details': {'owner_id': 7, 'x': i, 'y': 0}}
            for i in range(12)
        ]
        return {
            'status': 'research',
            'identity': {'pid': 1, 'start_ticks': '2'},
            'sample_monotonic': 100,
            'groups': {
                name: {'complete': True, 'units': units} for name, units in [('players', [player]), ('items', items)]
            },
        }

    return make


@pytest.fixture(autouse=True)
def fresh_read_caches():
    """The decoders' per-unit caches (game/decode.py `GOLD_SEEN`, `BASE_ROLLS_SEEN`) start empty in every test: unit
    ids repeat across the fakes."""
    from inventory_tracking.game import decode

    decode.GOLD_SEEN.clear()
    decode.BASE_ROLLS_SEEN.clear()
