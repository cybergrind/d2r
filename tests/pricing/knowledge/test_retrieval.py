import json
import socket

import pytest

from pricing.knowledge.__main__ import main
from pricing.knowledge.index import build_index
from pricing.knowledge.retrieval import item, recommend


def fact(name, level=12, quality='unique', **extra):
    return {
        'kind': 'item_fact',
        'item_id': name,
        'name': name,
        'aliases': [],
        'quality': quality,
        'slot': 'gloves',
        'requirements': {'level': level, 'strength': 0, 'dexterity': 0},
        'stats': [{'property': 'mana', 'min': 20, 'max': 20}],
        **extra,
    }


def advice(name, **extra):
    return {
        'kind': 'recommendation',
        'item_id': name,
        'name': name,
        'intent': 'recommend',
        'classes': ['sorceress', 'necromancer'],
        'archetypes': ['caster'],
        'side': 'player',
        'purpose': 'leveling',
        'reason': 'Mana helps sustained casting.',
        'conditions': [],
        'benefits': ['20 mana'],
        'evidence_strength': 'explicit',
        **extra,
    }


def publish(tmp_path, rows):
    path = tmp_path / 'portable.json'
    path.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    db = tmp_path / 'db.sqlite3'
    build_index([path], db)
    return db


@pytest.fixture
def corpus(tmp_path):
    return publish(
        tmp_path,
        [
            fact('Caster Gloves', aliases=['CG']),
            advice('Caster Gloves'),
            advice('Caster Gloves'),
            fact('Late', 26),
            advice('Late'),
            fact('Unknown', None),
            advice('Unknown'),
            fact('Vendor Ring', 1),
            advice('Vendor Ring', intent='vendor'),
            fact('Mention', 1),
            advice('Mention', intent='mention'),
            fact('Paired Set', 25, 'set'),
            advice('Paired Set', conditions=['Requires companion belt']),
            fact('Melee', 1),
            advice('Melee', classes=['barbarian'], archetypes=['melee']),
        ],
    )


def test_recommendation_is_bounded_deduplicated_and_filters_unknowns(corpus, monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: pytest.fail('Network access'))
    result = recommend(corpus, class_name='sorc', quality='uniq,set', max_level=25)
    assert {row['name'] for row in result['items']} == {'Caster Gloves', 'Paired Set'}
    assert result['total'] == 2
    assert result['query']['class'] == 'sorceress'
    pair = next(row for row in result['items'] if row['name'] == 'Paired Set')
    assert 'Requires companion belt' in pair['uses'][0]['conditions']
    assert pair['requirements']['level'] == 25
    assert pair['references']
    assert result['excluded_unknown_level'] == 1
    assert recommend(corpus, class_name='sorc', min_level=26, max_level=26)['items'][0]['name'] == 'Late'
    assert recommend(corpus, class_name='barbarian')['items'][0]['name'] == 'Melee'


def test_limits_and_detail_aliases_preserve_provenance(corpus):
    result = recommend(corpus, class_name='necro', limit=1)
    assert len(result['items']) == 1
    assert result['total'] == 2
    assert result['truncated']
    detail = item(corpus, 'cg', full=True)
    assert detail['items'][0]['name'] == 'Caster Gloves'
    assert detail['items'][0]['facts']['stats'][0]['min'] == 20
    assert detail['items'][0]['facts']['artifact']['locator'] == '/rows/0'
    assert item(corpus, 'unseen')['status'] == 'unknown'


@pytest.mark.parametrize(
    'kwargs',
    [
        {'class_name': 'fake'},
        {'max_level': 0},
        {'min_level': 26, 'max_level': 25},
        {'quality': 'magic'},
        {'archetype': 'fake'},
        {'limit': 0},
        {'side': 'bogus'},
    ],
)
def test_invalid_queries_fail_explicitly(corpus, kwargs):
    with pytest.raises(ValueError, match=r'Unknown|Supported|range|Limit'):
        recommend(corpus, **({'class_name': 'sorc'} | kwargs))


def test_cli_acceptance_and_default_disclosure(corpus, capsys):
    assert main(['--database', str(corpus), 'recommend', '--class', 'sorc', '--quality', 'uniq,set']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['query']['max_level'] == 25
    assert 'max_level' in result['defaults_applied']
    assert result['offline'] is True
    assert result['total'] == 2


def test_rebuild_updates_prepared_facts_and_preserves_previous_on_bad_identity(tmp_path):
    db = publish(tmp_path, [fact('A'), advice('A')])
    assert recommend(db, class_name='sorc')['total'] == 1
    db = publish(tmp_path, [fact('A', 30), advice('A')])
    assert recommend(db, class_name='sorc')['total'] == 0
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps({'schema_version': 1, 'rows': [fact('A'), fact('A', 3)]}))
    with pytest.raises(ValueError, match='Duplicate'):
        build_index([bad], db)
    assert item(db, 'A')['items'][0]['requirements']['level'] == 30


def test_ambiguous_alias_is_not_silently_resolved(tmp_path):
    db = publish(tmp_path, [fact('A', aliases=['same']), fact('B', aliases=['same'])])
    assert item(db, 'same')['status'] == 'ambiguous'


def test_appraisal_lookup_attaches_prepared_facts_and_utility(corpus):
    from pricing.knowledge.index import compact_result, lookup

    result = compact_result(lookup(corpus, 'Caster Gloves'))
    assert isinstance(result, dict)
    assert result['prepared']['items'][0]['requirements']['level'] == 12
    assert result['prepared']['items'][0]['uses'][0]['reason'] == 'Mana helps sustained casting.'


def test_default_caster_intent_and_explicit_melee_override(tmp_path):
    db = publish(
        tmp_path,
        [
            fact('Caster'),
            advice('Caster'),
            fact('Attack'),
            advice('Attack', archetypes=['melee']),
        ],
    )
    default = recommend(db, class_name='sorc')
    assert [r['name'] for r in default['items']] == ['Caster']
    assert default['query']['archetype'] == 'caster'
    assert [r['name'] for r in recommend(db, class_name='sorc', archetype='melee')['items']] == ['Attack']


def test_output_budget_pages_complete_records_without_losing_conditions(tmp_path, capsys):
    rows = []
    for i in range(20):
        name = f'Option {i:02d}'
        rows.extend([fact(name), advice(name, conditions=['Required companion ' + 'x' * 500])])
    db = publish(tmp_path, rows)
    assert main(['--database', str(db), 'recommend', '--class', 'sorc']) == 0
    stdout = capsys.readouterr().out
    assert len(stdout.encode()) <= 12 * 1024
    first = json.loads(stdout)
    seen = {r['item_id'] for r in first['items']}
    result = first
    while result['next_offset'] is not None:
        result = recommend(db, class_name='sorc', offset=result['next_offset'])
        assert not seen.intersection(r['item_id'] for r in result['items'])
        seen.update(r['item_id'] for r in result['items'])
        assert all(len(r['uses'][0]['conditions'][0]) > 500 for r in result['items'])
    assert len(seen) == 20


def test_missing_database_and_unknown_item_remain_offline(tmp_path, corpus, monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: pytest.fail('Network access'))
    with pytest.raises(FileNotFoundError, match='rebuild'):
        recommend(tmp_path / 'missing.sqlite3', class_name='sorc')
    assert item(corpus, 'Unknown Name')['status'] == 'unknown'


def test_stale_portable_dependency_rejected_and_previous_database_preserved(tmp_path):
    import hashlib

    facts = tmp_path / 'facts.json'
    recommendations = tmp_path / 'recommendations.json'
    facts.write_text(json.dumps({'schema_version': 1, 'rows': [fact('A')]}))
    recommendations.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [advice('A')],
                'inputs': {str(facts): hashlib.sha256(facts.read_bytes()).hexdigest()},
            }
        )
    )
    db = tmp_path / 'db.sqlite3'
    build_index([facts, recommendations], db)
    facts.write_text(json.dumps({'schema_version': 1, 'rows': [fact('A', 30)]}))
    with pytest.raises(ValueError, match='Stale portable dependency'):
        build_index([facts, recommendations], db)
    assert recommend(db, class_name='sorc')['total'] == 1
