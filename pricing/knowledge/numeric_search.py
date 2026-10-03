"""Optional numeric candidate index; final typed JSON predicates stay authoritative."""

import math


def build_numeric_index(connection):
    # No numeric affinity: preserve SQLite integers without rounding through REAL.
    connection.executescript("""
        CREATE TABLE evidence_numeric_properties (evidence_id INTEGER, property_id TEXT, value);
        INSERT INTO evidence_numeric_properties
            SELECT e.id, p.key, p.value
            FROM evidence e, json_each(e.payload, '$.properties') p
            WHERE p.type IN ('integer', 'real');
        CREATE INDEX numeric_property_lookup
            ON evidence_numeric_properties(property_id, value, evidence_id);
    """)


def candidate_clauses(connection, facets):
    predicates = [
        (str(key), value, '>=' if field == 'property_min' else '=')
        for field in ('properties', 'property_min')
        for key, value in (facets.get(field) or {}).items()
        if type(value) in (int, float) and math.isfinite(value)
    ]
    if (
        not predicates
        or not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='evidence_numeric_properties'"
        ).fetchone()
    ):
        # Existing published generations remain readable until the next rebuild.
        return [], []
    clauses, parameters = [], []
    for key, value, operator in predicates:
        clauses.append(
            f'e.id IN (SELECT evidence_id FROM evidence_numeric_properties WHERE property_id=? AND value {operator} ?)'
        )
        parameters.extend((key, value))
    return clauses, parameters
