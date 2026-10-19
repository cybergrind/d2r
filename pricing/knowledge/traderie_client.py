"""The one Traderie HTTP client: curl with a browser agent, retries, and a stop on a rate limit, challenge or
rejection (the refresh and pricing/tools share it)."""

import json
import subprocess
import time
from pathlib import Path
from tempfile import NamedTemporaryFile


API = 'https://traderie.com/api/diablo2resurrected'


USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'


class RequestRejected(OSError):
    """HTTP rejection or challenge: stop rather than retrying a denied request."""


class RateLimited(RequestRejected):
    """Server rate limit: stop this maintenance batch."""


def _fetch_response(url):
    with NamedTemporaryFile() as header_file:
        response = subprocess.run(
            [
                'curl',
                '--write-out',
                '\n%{http_code}',
                '--dump-header',
                header_file.name,
                '-sSL',
                '-A',
                USER_AGENT,
                '--max-time',
                '40',
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # curl includes proxy/redirect headers; only the final response applies.
        headers = {}
        for line in Path(header_file.name).read_text().splitlines():
            if line.startswith('HTTP/'):
                headers = {}
            elif ':' in line:
                name, value = line.split(':', 1)
                headers[name.strip().lower()] = value.strip()
    body, status = response.stdout.rsplit('\n', 1)
    return body, status, headers


def fetch_json(url):
    for attempt in range(3):
        try:
            body, status, headers = _fetch_response(url)
            if status == '429' or (status != '200' and 'Error 1015' in body):
                retry = headers.get('retry-after', 'unavailable')
                raise RateLimited(f'HTTP {status}; Retry-After: {retry}; stop batch: {url}')
            if headers.get('cf-mitigated', '').lower() == 'challenge':
                ray = headers.get('cf-ray', 'unavailable')
                raise RequestRejected(f'HTTP {status}; Cloudflare challenge; Ray ID: {ray}; stop batch: {url}')
            if status != '200':
                raise RequestRejected(f'HTTP {status}; request rejected: {url}')
            return json.loads(body)
        except RequestRejected:
            raise
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            if attempt == 2:
                raise OSError(f'JSON request failed: {url}: {error}') from error
            time.sleep(2**attempt)
    raise RuntimeError('unreachable')
