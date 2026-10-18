"""The service's restart on the code on disk, the macro's loop carried over (appraisal/service.py `Restart`)."""

import json
import threading
import time
from pathlib import Path

from inventory_tracking.appraisal.service import (
    RESTART_FILE,
    RESUME_FILE,
    RESUME_SECONDS,
    read_resume,
    restart_asked,
    write_resume,
)
from inventory_tracking.macros.pickmode import MODES
from inventory_tracking.macros.runner import MacroRunner


def test_a_restart_is_asked_for_once_by_its_file_with_the_state_to_come_back_in(tmp_path: Path) -> None:
    assert restart_asked(tmp_path) is None
    (tmp_path / RESTART_FILE).touch()
    assert restart_asked(tmp_path) == {}  # the state as it is
    assert restart_asked(tmp_path) is None
    (tmp_path / RESTART_FILE).write_text('{"loop": true}')  # the loop on with no press of KP_6
    assert restart_asked(tmp_path) == {'loop': True}


def test_the_macros_state_is_read_back_once_and_not_when_old(tmp_path: Path) -> None:
    write_resume(tmp_path, {'loop': True, 'pickup_mode': MODES[1]})
    assert read_resume(tmp_path) == {'loop': True, 'pickup_mode': MODES[1], 'written': ANY}
    assert read_resume(tmp_path) is None
    (tmp_path / RESUME_FILE).write_text(json.dumps({'loop': True, 'written': time.time() - RESUME_SECONDS - 1}))
    assert read_resume(tmp_path) is None


class _Any:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, float)


ANY = _Any()


def test_the_loop_on_before_a_restart_is_on_again_at_the_first_poll_that_reads_the_game() -> None:
    started = []
    before = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'))
    before.loop.on, before.pickup_mode = True, MODES[1]
    state = before.resume_state()
    assert {key: state[key] for key in ('loop', 'pickup_mode')} == {'loop': True, 'pickup_mode': MODES[1]}

    after = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=Path('/nonexistent'),
        execute=lambda cancelled, routine: started.append(routine),
        place=lambda: ('cyber40', 103),
    )
    after.resume(state)
    assert after.pickup_mode == MODES[1]
    assert not after.loop.on
    after.poll(10.0)
    assert after.loop.on
    if after.thread is not None:
        after.thread.join(5)
    after.close()
