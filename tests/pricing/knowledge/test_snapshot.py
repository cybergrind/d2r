import json
import sqlite3

import pytest

from pricing.knowledge.assessment.market_repository import market_rows
from pricing.knowledge.index import build_index, index_status
from pricing.knowledge.snapshot import read_snapshot


def test_snapshot_borrowers_keep_transaction_open_and_failure_closes_connection(tmp_path):
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    opened = []

    def fail_assessment():
        with read_snapshot(database) as connection:
            opened.append(connection)
            assert index_status(connection)['records'] == 0
            assert market_rows(connection, 'Ring') == []
            assert connection.in_transaction
            with pytest.raises(sqlite3.OperationalError, match='readonly'):
                connection.execute('DELETE FROM evidence')
            raise RuntimeError('assessment failed')

    with pytest.raises(RuntimeError, match='assessment failed'):
        fail_assessment()
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        opened[0].execute('SELECT 1')
