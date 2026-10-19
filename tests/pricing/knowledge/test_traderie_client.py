import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from pricing.knowledge import refresh, traderie_client


def response(monkeypatch, status, body, headers=''):
    def run(args, **kwargs):
        if '--dump-header' in args:
            Path(args[args.index('--dump-header') + 1]).write_text(headers)
        return subprocess.CompletedProcess(args, 0, f'{body}\n{status}')

    request = Mock(side_effect=run)
    monkeypatch.setattr(traderie_client.subprocess, 'run', request)
    monkeypatch.setattr(traderie_client.time, 'sleep', Mock())
    return request


@pytest.mark.parametrize(
    ('status', 'body', 'headers', 'message'),
    [
        ('403', '<html>Just a moment...</html>', 'cf-mitigated: challenge\r\n', 'Cloudflare challenge'),
        ('403', '{"error":"Forbidden"}', '', 'HTTP 403'),
        ('401', '{"error":"Unauthorized jwt"}', '', 'HTTP 401'),
        ('200', '<html>challenge</html>', 'CF-Mitigated: challenge\r\n', 'Cloudflare challenge'),
    ],
)
def test_rejected_responses_stop_without_retry(monkeypatch, status, body, headers, message):
    request = response(monkeypatch, status, body, headers)
    with pytest.raises(OSError, match=message):
        traderie_client.fetch_json('https://traderie.com/api/test')
    assert request.call_count == 1
    sleep = traderie_client.time.sleep
    assert isinstance(sleep, Mock)  # patched by response()
    sleep.assert_not_called()


def test_rate_limit_preserves_retry_after(monkeypatch):
    request = response(monkeypatch, '429', '<html>limited</html>', 'Retry-After: 120\r\n')
    with pytest.raises(traderie_client.RateLimited, match='Retry-After: 120'):
        traderie_client.fetch_json('https://traderie.com/api/test')
    assert request.call_count == 1


def test_success_uses_browser_user_agent(monkeypatch):
    request = response(monkeypatch, '200', '{"listings": []}')
    assert traderie_client.fetch_json('https://traderie.com/api/test') == {'listings': []}
    args = request.call_args.args[0]
    assert 'Chrome/' in args[args.index('-A') + 1]


def test_invalid_json_retries_then_preserves_cause(monkeypatch):
    request = response(monkeypatch, '200', 'invalid')
    with pytest.raises(OSError, match='JSON request failed'):
        traderie_client.fetch_json('https://traderie.com/api/test')
    assert request.call_count == 3


def test_refresh_job_preserves_rejection_and_stops_pages():
    fetch = Mock(side_effect=refresh.RequestRejected('HTTP 403; Cloudflare challenge'))
    job = refresh.refresh_item({'id': '1', 'name': 'Rockfleece'}, fetch, {})
    assert job['terminal_reason'] == 'request_rejected'
    assert 'Cloudflare challenge' in job['error']
    assert job['next_page'] == 0
    fetch.assert_called_once_with(0)
