"""Pin one read-only index generation for a multi-query appraisal."""

from contextlib import contextmanager
from pathlib import Path

from pricing.knowledge.index import _connect, index_status


@contextmanager
def read_snapshot(database):
    connection = _connect(database)
    try:
        connection.execute('BEGIN')
        # Establish the read snapshot before assessment or other work can publish
        # a replacement. Nested repositories borrow this connection via _connect.
        connection.execute("SELECT value FROM metadata WHERE key='build'").fetchone()
        yield connection
    finally:
        connection.close()


def verify_definition_generation(connection, definitions, source_path):
    verify_artifact_generation(connection, definitions.generation, source_path, 'definitions')


def verify_artifact_generation(connection, generation, source_path, label):
    source_path = Path(source_path).resolve()
    indexed = [
        row['sha256'] for row in index_status(connection)['sources'] if Path(row['path']).resolve() == source_path
    ]
    # Partial indexes may contain only observations, with no duplicate definition
    # source to reconcile. If the artifact is indexed, its bytes must agree.
    if indexed and indexed != [generation]:
        raise ValueError(f'Offline {label} and index generations differ; run python -m pricing.knowledge rebuild')
