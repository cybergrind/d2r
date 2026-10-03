from pricing.triage.rule_index import candidates, compile_index


def test_index_preserves_wildcards_casefold_order_and_pattern_overrides():
    rows = [
        {'name': 'Example', 'bucket': 'name-first'},
        {'category': 'base', 'bucket': 'category'},
        {'category': 'rare', 'name': 'other', 'pattern': {'category': 'base', 'name': 'Example'}},
        {'bucket': 'wildcard'},
        {'category': 'base', 'family': 'shield', 'bucket': 'family'},
        {'category': 'base', 'family': 'sword', 'bucket': 'unrelated'},
    ]
    item = {'category': 'BASE', 'name': 'EXAMPLE', 'family': 'shield'}
    assert candidates(item, compile_index(rows)) == [rows[i] for i in (0, 1, 3, 4)]
    assert candidates(item, compile_index(rows, patterns=True)) == [rows[2]]
    assert candidates({}, compile_index(rows)) == [rows[3]]
