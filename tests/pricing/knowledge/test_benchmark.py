"""Benchmark accounting must preserve observed tails and actual query plans."""

from pricing.knowledge.benchmark import summary


def test_summary_retains_tail_and_sample_count():
    result = summary(list(range(1, 31)))
    assert result == {'samples': 30, 'p50': 15.5, 'p95': 29, 'min': 1, 'max': 30}


def test_recommendation_measurement_records_decode_and_projection(tmp_path):
    import json

    from pricing.knowledge.benchmark import phase_sample
    from pricing.knowledge.index import build_index

    source = tmp_path / 'facts.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Fixture',
                        'kind': 'item_fact',
                        'item_id': 'fixture',
                        'quality': 'unique',
                        'requirements': {'level': 5},
                    },
                    {
                        'name': 'Fixture',
                        'kind': 'recommendation',
                        'item_id': 'fixture',
                        'intent': 'recommend',
                        'classes': ['sorceress'],
                        'reason': 'Fixture recommendation',
                    },
                ],
            }
        )
    )
    database = tmp_path / 'index.sqlite3'
    build_index([source], database)
    sample = phase_sample(database, ['recommend'])
    assert sample is not None
    timings, statements = sample
    assert timings['json_decode_ms'] > 0
    assert timings['compact_projection_ms'] > 0
    assert timings['database_execute_fetch_ms'] == timings['sqlite_execute_ms'] + timings['sqlite_fetch_ms']
    assert any('FROM item_uses' in sql for sql, _ in statements)
