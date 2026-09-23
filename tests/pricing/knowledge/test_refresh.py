from pricing.knowledge.refresh import refresh_item


def test_refresh_continues_past_wrong_scope_page_and_resumes():
    calls = []

    def fetch(page):
        calls.append(page)
        if page == 0:
            return {'listings': [{'id': '1', 'properties': []}], 'nextPage': 1}
        return {'listings': []}

    job = refresh_item({'id': 'x', 'name': 'Item', 'type': 'base'}, fetch, {}, page_cap=3)
    assert calls == [0, 1]
    assert job['terminal_reason'] == 'source_exhausted'
    assert job['scoped_observations'] == 0
    refresh_item({'id': 'x', 'name': 'Item', 'type': 'base'}, fetch, {}, previous=job)
    assert calls == [0, 1]


def test_refresh_budget_failure_is_visible():
    def fetch(page):
        raise ValueError('bad response')

    job = refresh_item({'id': 'x', 'name': 'Item', 'type': 'base'}, fetch, {}, page_cap=2)
    assert job['terminal_reason'] == 'fetch_error'
    assert job['error'] == 'bad response'


def test_rate_limit_job_preserves_retry_reason():
    from pricing.knowledge.refresh import RateLimited

    def fetch(page):
        raise RateLimited('HTTP 429; Retry-After unavailable')

    job = refresh_item({'id': 'x', 'name': 'Item', 'type': 'base'}, fetch, {})
    assert job['terminal_reason'] == 'rate_limited'
    assert job['next_page'] == 0
