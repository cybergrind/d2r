import json
import logging
from concurrent.futures import Future
from pathlib import Path

from inventory_tracking.appraisal import service as appraisal_service
from inventory_tracking.appraisal.worker import AppraisalWorker


class Deferred:
    def __init__(self):
        self.jobs = []

    def submit(self, function, *args):
        future = Future()
        self.jobs.append((future, function, args))
        return future

    def run(self, index):
        future, function, args = self.jobs[index]
        if future.set_running_or_notify_cancel():
            future.set_result(function(*args))


class Capture:
    def freeze(self):
        return {'observation': {'item': {}}, 'captured_at': 'now'}

    def still_selected(self, frozen):
        return True


def test_new_request_cannot_be_replaced_by_old_result():
    pool = Deferred()
    output = []
    worker = AppraisalWorker(Capture(), lambda _: {'evidence': 1}, output.append, pool)
    worker.request(1, 1)
    # Simulate old retrieval already running (cannot be cancelled).
    old = pool.jobs[0]
    old[0].set_running_or_notify_cancel()
    worker.request(2, 2)
    old[1](*old[2])
    assert output[-1]['request_id'] == 2
    assert output[-1]['state'] == 'captured'
    pool.run(1)
    assert output[-1]['request_id'] == 2
    assert output[-1]['state'] == 'complete'


def test_debounce_and_delayed_request_do_not_capture():
    pool = Deferred()
    output = []
    worker = AppraisalWorker(Capture(), lambda _: {}, output.append, pool)
    assert worker.request(1, 1)
    assert not worker.request(1.1, 1.1)
    assert not worker.request(2, 4)
    assert len(pool.jobs) == 1


def test_changed_selection_suppresses_evidence():
    capture = Capture()
    capture.still_selected = lambda _: False
    pool = Deferred()
    output = []
    worker = AppraisalWorker(capture, lambda _: {'secret_evidence': True}, output.append, pool)
    worker.request(1, 1)
    pool.run(0)
    assert output[-1]['state'] == 'rejected'
    assert 'result' not in output[-1]


def test_only_current_draft_reaches_text_files_and_log(tmp_path, monkeypatch, caplog):
    record = json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_result.json').read_text())
    monkeypatch.setattr(appraisal_service, 'notify', lambda *_: None)
    pool = Deferred()
    worker = AppraisalWorker(
        Capture(), lambda _: record['result'], lambda r: appraisal_service.publish_request(tmp_path, r), pool
    )
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        worker.request(1, 1)
        old = pool.jobs[0]
        old[0].set_running_or_notify_cancel()
        worker.request(2, 2)
        old[1](*old[2])
        assert not (tmp_path / 'request-1/appraisal.txt').exists()
        pool.run(1)
    text = (tmp_path / 'request-2/appraisal.txt').read_text()
    assert text in caplog.text
    assert '\n  +10% Faster Cast Rate\n' in text
    assert sum('Observed stats:' in r.message for r in caplog.records) == 1
    assert json.loads((tmp_path / 'latest.json').read_text())['request_id'] == 2


def test_unknown_panel_is_saved_without_submitting_an_appraisal(tmp_path, monkeypatch):
    from inventory_tracking.appraisal.capture import SelectionUnavailable

    diagnostics = {'validated': False, 'initial': {'panel': 'unknown'}, 'expanded': {'grids': []}}

    class UnknownPanel(Capture):
        def freeze(self):
            raise SelectionUnavailable('Unsupported inventory widget', diagnostics)

    notifications = []
    monkeypatch.setattr(appraisal_service, 'notify', lambda *args: notifications.append(args))
    pool = Deferred()
    worker = AppraisalWorker(
        UnknownPanel(), lambda _: None, lambda r: appraisal_service.publish_request(tmp_path, r), pool
    )
    assert worker.request(1, 1)
    assert not pool.jobs
    directory = tmp_path / 'request-1'
    assert json.loads((directory / 'panel-diagnostics.json').read_text()) == diagnostics
    report = json.loads((directory / 'report.json').read_text())
    assert report['state'] == 'rejected'
    assert 'result' not in report
    assert 'diagnostics' not in report
    assert report['diagnostics_file'] in (directory / 'appraisal.txt').read_text()
    assert 'diagnostics saved' in notifications[-1][1]
