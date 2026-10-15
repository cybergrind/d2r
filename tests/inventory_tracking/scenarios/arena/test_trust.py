"""trust.py: the calibration's verdicts as a test reads them, and the skip of a scene not believed."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.inventory_tracking.scenarios.arena.trust import FIXTURES, REPORT, VERDICTS, needs_trust, reason, trusted


REPO = Path(__file__).resolve().parents[4]
TABLE = """\
# Calibration of the arena

| all | scenes | ratio |
| --- | ---: | ---: |
| all | 3 | 9.99 |

| scene | kind | seconds | taken take | taken arena | ratio | kills take | kills arena | ratio | trusted | notes |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | --- |
| good-1-burst | burst | 8.0 | 400 | 500 | 1.25 (1.10 to 1.40) | 4 | 3 | 0.75 | yes | assumed: hand |
| harsh-2-burst | burst | 8.0 | 400 | 2000 | 5.00 (4.80 to 5.10) | 4 | 4 | 1.00 | no | died in the arena at 2.0 s |
| quiet-3-long | long | 8.0 | 0 | 0 | - | 0 | 0 | 1.00 | no | |
"""


@pytest.fixture
def fixtures(tmp_path: Path) -> Path:
    (tmp_path / VERDICTS).write_text(json.dumps({'good-1-burst': True, 'harsh-2-burst': False, 'quiet-3-long': False}))
    (tmp_path / REPORT).write_text(TABLE)
    return tmp_path


def test_a_scene_is_trusted_as_the_file_says_and_an_unknown_one_is_not(fixtures: Path):
    assert trusted('good-1-burst', fixtures)
    assert not trusted('harsh-2-burst', fixtures)
    assert not trusted('never-cut', fixtures)


def test_nothing_is_trusted_without_the_file(tmp_path: Path):
    assert not trusted('good-1-burst', tmp_path)
    assert needs_trust('good-1-burst', tmp_path).args == (True,)


def test_only_true_is_trust(tmp_path: Path):
    (tmp_path / VERDICTS).write_text(json.dumps({'a': 'yes', 'b': 1, 'c': None}))
    assert not any(trusted(name, tmp_path) for name in 'abc')


def test_a_trusted_scene_gets_a_mark_that_skips_nothing(fixtures: Path):
    mark = needs_trust('good-1-burst', fixtures)
    assert (mark.name, mark.args) == ('skipif', (False,))


def test_an_untrusted_scene_is_skipped_with_its_ratios_as_the_reason(fixtures: Path):
    mark = needs_trust('harsh-2-burst', fixtures)
    assert (mark.name, mark.args) == ('skipif', (True,))
    told = mark.kwargs['reason']
    assert 'harsh-2-burst' in told
    assert '5.00 (4.80 to 5.10) for the life lost' in told
    assert '1.00 for the kills' in told
    assert 'died in the arena at 2.0 s' in told


def test_a_scene_without_a_ratio_says_so(fixtures: Path):
    assert '- for the life lost and 1.00 for the kills' in reason('quiet-3-long', fixtures)


def test_a_scene_never_calibrated_is_skipped_and_says_that(fixtures: Path):
    mark = needs_trust('never-cut', fixtures)
    assert mark.args == (True,)
    assert 'not calibrated for never-cut' in mark.kwargs['reason']


def test_a_verdict_without_a_row_in_the_report_is_not_given_ratios(tmp_path: Path):
    (tmp_path / VERDICTS).write_text(json.dumps({'harsh-2-burst': False}))
    assert 'not calibrated' in reason('harsh-2-burst', tmp_path)


PLAYED = """
from pathlib import Path
import pytest
from tests.inventory_tracking.scenarios.arena.trust import needs_trust

FIXTURES = Path({fixtures!r})

@needs_trust('good-1-burst', FIXTURES)
def test_believed():
    pass

@needs_trust('harsh-2-burst', FIXTURES)
def test_not_believed():
    raise AssertionError('a safety verdict in a world that is not believed')

@pytest.mark.parametrize('name', [
    pytest.param(name, marks=needs_trust(name, FIXTURES)) for name in ('good-1-burst', 'never-cut')
])
def test_each(name):
    assert name == 'good-1-burst'
"""  # ruff: ignore[missing-f-string-syntax] a template: filled by .format


def test_the_mark_skips_and_lets_run(fixtures: Path, tmp_path: Path):
    """A pytest of its own over three tests that carry the mark, as a decorator and in a `param`."""
    played = tmp_path / 'played'
    played.mkdir()
    (played / 'test_played.py').write_text(PLAYED.format(fixtures=str(fixtures)))
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', str(played), '-rs', '-q', '-p', 'no:cacheprovider', '--rootdir', str(played)],
        capture_output=True, text=True, check=False, cwd=played, env={**os.environ, 'PYTHONPATH': str(REPO)},
    )  # fmt: skip
    assert '2 passed, 2 skipped' in result.stdout, result.stdout + result.stderr
    assert '5.00 (4.80 to 5.10) for the life lost' in result.stdout
    assert 'not calibrated for never-cut' in result.stdout


def test_the_hosts_verdicts_are_read():
    """The file calibrate.py wrote: every verdict a plain true or false, and `trusted` agrees with it."""
    found = json.loads((FIXTURES / VERDICTS).read_text(encoding='utf-8'))
    assert found
    assert all(isinstance(verdict, bool) for verdict in found.values())
    assert all(trusted(name) == verdict for name, verdict in found.items())
    untrusted = next((name for name, verdict in found.items() if not verdict), None)
    if untrusted is not None:
        assert untrusted in needs_trust(untrusted).kwargs['reason']
        assert 'not calibrated' not in needs_trust(untrusted).kwargs['reason']
