import json
import socket

import pytest

from pricing.knowledge.index import build_index, lookup, search


@pytest.fixture
def corpus(tmp_path):
    source = tmp_path / 'evidence.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'sources': [{'id': 'guide', 'url': 'https://example.test/guide', 'sha256': 'abc'}],
                'rows': [
                    {
                        'name': 'Greater Talons',
                        'kind': 'base_rule',
                        'sockets': 3,
                        'source_id': 'guide',
                        'details': {'runeword': 'Mosaic'},
                    },
                    {
                        'name': 'Greater Talons',
                        'kind': 'base_rule',
                        'sockets': 2,
                        'source_id': 'guide',
                        'details': {'runeword': 'Pattern'},
                    },
                    {
                        'name': 'Greater Talons',
                        'kind': 'demand',
                        'side': 'player',
                        'class': 'Assassin',
                        'build': 'example',
                        'variant': 'starter',
                    },
                    {
                        'name': 'Bloodfist',
                        'kind': 'leveling',
                        'category': 'gloves',
                        'details': {'reason': 'early attack speed'},
                    },
                    {
                        'name': 'Sazabi\u2019s Mental Sheath',
                        'kind': 'demand',
                        'side': 'merc',
                        'details': {'reason': 'mercenary set'},
                    },
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    return source, db


def test_lookup_is_offline_and_exact_facets_do_not_leak(corpus, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Offline retrieval attempted a network connection')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    result = lookup(corpus[1], 'Greater Talons', sockets=3)
    assert result['status'] == 'known'
    assert [r['details']['runeword'] for r in result['evidence']['base_rule']] == ['Mosaic']
    assert result['evidence']['demand'][0]['class'] == 'Assassin'
    assert result['evidence']['base_rule'][0]['source']['sha256'] == 'abc'
    assert result['price_status'] == 'unresolved'
    missing = lookup(corpus[1], 'Uncatalogued Rare')
    assert missing['status'] == 'unknown'
    assert missing['price_status'] == 'unresolved'
    assert 'vendor' not in json.dumps(missing).lower()


def test_leveling_utility_does_not_require_market_price(corpus):
    result = lookup(corpus[1], 'Bloodfist')
    assert result['evidence']['leveling']
    assert result['price_status'] == 'unresolved'


def test_typographic_names_and_fts_facets(corpus):
    assert lookup(corpus[1], "Sazabi's Mental Sheath")['status'] == 'known'
    assert search(corpus[1], 'attack', kind='leveling')[0]['name'] == 'Bloodfist'
    assert search(corpus[1], 'attack', kind='demand') == []
    assert search(corpus[1], '', side='merc')[0]['name'] == 'Sazabi\u2019s Mental Sheath'
    assert search(corpus[1], '" OR * : (') == []


def test_failed_rebuild_preserves_previous_database(corpus, tmp_path):
    bad = tmp_path / 'bad.json'
    bad.write_text('{broken')
    with pytest.raises(ValueError, match='Expecting property name'):
        build_index([bad], corpus[1])
    assert lookup(corpus[1], 'Bloodfist')['status'] == 'known'


def test_no_database_gives_actionable_offline_error(tmp_path):
    with pytest.raises(FileNotFoundError, match='rebuild'):
        lookup(tmp_path / 'missing.sqlite3', 'Bloodfist')


def test_jsonl_rebuild_preserves_all_observations_and_provenance(tmp_path):
    source = tmp_path / 'observations.jsonl'
    rows = [
        {
            'name': 'Bloodfist',
            'kind': 'market',
            'seller_id': f'seller-{i}',
            'source': {'url': 'https://example.test/asks'},
            'amount': 1,
        }
        for i in range(3)
    ]
    source.write_text('\n'.join(json.dumps(r) for r in rows))
    db = tmp_path / 'index.sqlite3'
    report = build_index([source], db)
    assert report['records'] == 3
    assert report['sources'][0]['sha256']


def test_magical_quality_cannot_use_runeword_recipe(tmp_path):
    source = tmp_path / 'recipes.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Test Base',
                        'kind': 'base_rule',
                        'sockets': 3,
                        'predicates': {'quality': ['normal', 'superior', 'low_quality']},
                        'details': {'runeword': 'Test Recipe'},
                    }
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    assert 'base_rule' not in lookup(db, 'Test Base', rarity='rare', sockets=3)['evidence']


def test_market_facets_preserve_watch_vs_comparable_distinction(tmp_path):
    source = tmp_path / 'market.jsonl'
    source.write_text(
        json.dumps(
            {
                'name': 'Test Item',
                'kind': 'market',
                'evidence_kind': 'ask',
                'rarity': 'rare',
                'sockets': 2,
                'scope_status': 'verified',
                'unit_policy': 'single_item',
                'seller_id': 'seller',
                'ask_ist': 1.0,
                'observed_at': '2026-09-23',
                'properties': {'999': 3},
            }
        )
        + '\n'
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    result = lookup(db, 'Test Item', sockets=2, properties={'999': 3})
    assert result['market']['priced_sellers'] == 1
    assert result['price_status'] == 'comparable_evidence_requires_roll_review'
    miss = lookup(db, 'Test Item', sockets=3)
    assert miss['price_status'] == 'unresolved'


def test_planner_quality_code_is_not_a_recipe_predicate(tmp_path):
    source = tmp_path / 'planner.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {'name': 'Magic Grand Charm', 'kind': 'demand', 'rarity': 'magic', 'predicates': {'quality': 4}}
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    assert lookup(db, 'Magic Grand Charm', rarity='magic')['evidence']['demand']


def test_class_facets_include_shared_planner_associations_case_insensitively(tmp_path):
    source = tmp_path / 'associations.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Spirit',
                        'kind': 'demand',
                        'class': 'Multiple',
                        'build': 'shared-planner',
                        'predicates': {'sockets': 4},
                        'details': {'related_classes': ['Sorceress', 'Paladin'], 'related_builds': ['nova-sorceress']},
                    }
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    assert search(db, '', **{'class': 'sorceress'})
    assert search(db, '', build='nova-sorceress')
    assert lookup(db, 'Spirit', **{'class': 'SORCERESS'})['evidence']['demand']
    assert 'demand' not in lookup(db, 'Spirit', sockets=0)['evidence']


def test_verified_base_relation_finds_magic_patterns_without_fuzzy_identity(tmp_path):
    source = tmp_path / 'bases.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Magic Grand Charm',
                        'kind': 'demand',
                        'rarity': 'magic',
                        'aliases': ['Source Charm Label'],
                        'details': {'base_name': 'Grand Charm'},
                    }
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    assert lookup(db, 'Grand Charm', rarity='magic')['evidence']['demand']
    assert lookup(db, 'Source Charm Label')['evidence']['demand']


def test_legacy_recipe_recommendation_is_not_applicable_to_magic_or_filled_base(tmp_path):
    source = tmp_path / 'legacy-recipe.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Crystal Sword',
                        'kind': 'base_rule',
                        'sockets': 4,
                        'details': {'runeword': 'Spirit', 'legality': 'recommendation_only'},
                    }
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    assert 'base_rule' not in lookup(db, 'Crystal Sword', rarity='magic', sockets=4)['evidence']
    assert 'base_rule' not in lookup(db, 'Crystal Sword', properties={'934': 'Ist Rune'})['evidence']
