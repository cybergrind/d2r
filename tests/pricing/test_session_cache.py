import os

import pytest

from pricing.knowledge.assessment import build_profiles
from pricing.knowledge.assessment.compile import stat_configurations
from tests.pricing import session_cache
from tests.pricing.session_cache import memoize


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(session_cache, 'ROOT', str(tmp_path))
    (tmp_path / 'input.json').write_text('[1]')
    return tmp_path


def reader(path, calls):
    def read(name='input.json'):
        calls.append(name)
        return {'value': (path / name).read_text()}

    return read


def test_hit_serves_a_fresh_copy(tree):
    calls = []
    read = memoize(reader(tree, calls), lambda name='input.json': name)
    first = read()
    first['value'] = 'mutated'
    assert read() == {'value': '[1]'}
    assert read() is not read()
    assert calls == ['input.json']


def test_changed_input_or_new_neighbour_recomputes(tree):
    calls = []
    read = memoize(reader(tree, calls), lambda name='input.json': name)
    read()
    (tree / 'input.json').write_text('[22]')
    assert read() == {'value': '[22]'}
    before = os.stat(tree).st_mtime_ns
    (tree / 'added.json').write_text('{}')
    os.utime(tree, ns=(before + 10**9, before + 10**9))  # the directory's mtime may not tick within a test
    read()
    assert len(calls) == 3


def test_no_key_bypasses(tree):
    calls = []
    read = memoize(reader(tree, calls), lambda name='input.json': None)
    read()
    read()
    assert len(calls) == 2


def test_outer_entry_depends_on_files_an_inner_hit_served(tree):
    inner = memoize(reader(tree, []), lambda name='input.json': name)
    calls = []

    def outer_function():
        calls.append(1)
        return inner()

    outer = memoize(outer_function, lambda: 'outer')
    inner()  # cached first, so the outer call opens no file itself
    outer()
    (tree / 'input.json').write_text('[333]')
    assert outer() == {'value': '[333]'}
    assert calls == [1, 1]


@pytest.mark.skipif(os.environ.get('D2R_PRICING_CACHE') == 'off', reason='caches turned off')
def test_pricing_session_installs_the_caches():
    assert hasattr(build_profiles.build, '__wrapped__')
    assert hasattr(stat_configurations.compile_stat_configurations, '__wrapped__')
    first = build_profiles.build()
    second = build_profiles.build()
    assert first == second
    assert first is not second
