"""Rebuildable SQLite evidence index. This module never accesses the network."""

import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import unicodedata
from pathlib import Path


SCHEMA_VERSION = 1
DATABASE_VERSION = 3
FACETS = ('kind', 'category', 'rarity', 'sockets', 'ethereal', 'side', 'class', 'build', 'variant')


def normalize_name(value):
    """Normalize typography, not item identity or meaningful modifiers."""
    value = unicodedata.normalize('NFKC', str(value)).casefold().replace('\u2019', "'")
    return ' '.join(value.split())


def _scalar(value):
    if isinstance(value, dict):
        return value.get('name') or value.get('slug') or value.get('id')
    if isinstance(value, list):
        return None
    return value


def _facet_values(row, facet):
    value = _scalar(row.get(facet))
    if value is None and facet == 'rarity':
        value = row.get('quality')
    if value is None and facet in ('sockets', 'ethereal'):
        value = row.get('predicates', {}).get(facet)
    values = [] if value is None else [value]
    association = {'class': 'related_classes', 'build': 'related_builds'}.get(facet)
    if association:
        values.extend(row.get('details', {}).get(association, []))
    if facet == 'base_name' and row.get('details', {}).get('base_name'):
        values.append(row['details']['base_name'])
    if facet == 'alias':
        values.extend(row.get('aliases', []))
    return [normalize_name(value) if isinstance(value, str) else value for value in values]


def _search_body(row):
    """Index useful language, not repeated raw property options, hashes and IDs."""
    excluded = {'raw_item', 'raw_properties', 'properties', 'stats', 'mods', 'item_definition'}
    details = {key: value for key, value in row.get('details', {}).items() if key not in excluded}
    return json.dumps({key: row.get(key) for key in FACETS} | {'details': details}, ensure_ascii=False)


def _read_rows(path):
    if path.suffix == '.jsonl':
        with path.open() as stream:
            for number, line in enumerate(stream, 1):
                if line.strip():
                    yield json.loads(line), f'line:{number}'
        return
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get('schema_version') != SCHEMA_VERSION:
        raise ValueError(f'Unsupported evidence schema: {path}')
    sources = data.get('sources', [])
    source_map = sources if isinstance(sources, dict) else {s['id']: s for s in sources}
    for number, original in enumerate(data['rows']):
        row = dict(original)
        if row.get('affix_table') and data.get('affix_pools'):
            referenced = {
                key
                for field in ('range_pools', 'rare_range_pools')
                for stats in row.get(field, {}).values()
                for key in stats.values()
            }
            row['tier_pools'] = {key: data['affix_pools'][key] for key in referenced}
        if 'source' not in row and row.get('source_id') in source_map:
            row['source'] = source_map[row['source_id']]
        yield row, f'/rows/{number}'


def build_index(paths, database):
    """Validate and atomically replace the database, preserving it on any failure."""
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.appraisal-', suffix='.sqlite3', dir=database.parent)
    os.close(fd)
    report = {'schema_version': SCHEMA_VERSION, 'records': 0, 'sources': [], 'by_kind': {}}
    try:
        with sqlite3.connect(temporary) as connection:
            connection.executescript("""
                CREATE TABLE evidence (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL,
                    kind TEXT NOT NULL, category TEXT, rarity TEXT, sockets INTEGER, ethereal INTEGER,
                    side TEXT, class TEXT, build TEXT, variant TEXT, payload TEXT NOT NULL
                );
                CREATE INDEX evidence_name ON evidence(normalized_name);
                CREATE INDEX evidence_facets ON evidence(kind, category, rarity, sockets, ethereal);
                CREATE INDEX evidence_demand ON evidence(class, side, build);
                CREATE TABLE associations (evidence_id INTEGER, facet TEXT, value TEXT);
                CREATE INDEX association_lookup ON associations(facet,value,evidence_id);
                CREATE VIRTUAL TABLE evidence_fts USING fts5(name, body, tokenize='unicode61');
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            prepared_rows = []
            prepared_coverage = {}
            portable_dependencies = []
            for source_path in sorted(map(Path, paths)):
                digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
                source_count = 0
                prepared_start = len(prepared_rows)
                for original, locator in _read_rows(source_path):
                    row = dict(original)
                    if not row.get('name') or not row.get('kind'):
                        raise ValueError(f'Evidence needs name and kind: {source_path} {locator}')
                    row['artifact'] = {'path': str(source_path), 'locator': locator, 'sha256': digest}
                    if row['kind'] in ('item_fact', 'recommendation'):
                        prepared_rows.append(row)
                    values = [str(row['name']), normalize_name(row['name'])]
                    values.extend(next(iter(_facet_values(row, key)), None) for key in FACETS)
                    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                    cursor = connection.execute(
                        'INSERT INTO evidence VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)', (*values, payload)
                    )
                    connection.execute(
                        'INSERT INTO evidence_fts(rowid,name,body) VALUES (?,?,?)',
                        (cursor.lastrowid, row['name'], _search_body(row)),
                    )
                    for facet in ('class', 'build', 'base_name', 'alias'):
                        connection.executemany(
                            'INSERT INTO associations VALUES (?,?,?)',
                            [(cursor.lastrowid, facet, value) for value in set(_facet_values(row, facet))],
                        )
                    source_count += 1
                    kind = row['kind']
                    report['by_kind'][kind] = report['by_kind'].get(kind, 0) + 1
                if len(prepared_rows) > prepared_start and source_path.suffix == '.json':
                    document = json.loads(source_path.read_text())
                    prepared_coverage[str(source_path)] = document.get('coverage', {})
                    portable_dependencies.extend(document.get('inputs', {}).items())
                report['records'] += source_count
                report['sources'].append({'path': str(source_path), 'sha256': digest, 'records': source_count})
            for dependency, expected_hash in portable_dependencies:
                matches = [entry for entry in report['sources'] if Path(entry['path']).name == Path(dependency).name]
                if matches and (len(matches) != 1 or matches[0]['sha256'] != expected_hash):
                    raise ValueError(f'Stale portable dependency: {dependency}; regenerate its dependent artifact')
            from pricing.knowledge.retrieval import publish

            report['retrieval'] = publish(connection, prepared_rows)
            connection.execute(
                'INSERT INTO metadata VALUES (?,?)', ('prepared_coverage', json.dumps(prepared_coverage))
            )
            connection.execute('INSERT INTO metadata VALUES (?,?)', ('build', json.dumps(report, sort_keys=True)))
            connection.execute(f'PRAGMA user_version={DATABASE_VERSION}')
            connection.execute("INSERT INTO evidence_fts(evidence_fts) VALUES('integrity-check')")
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Database integrity check failed')
        os.replace(temporary, database)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return report


def _connect(database):
    database = Path(database)
    if not database.is_file():
        raise FileNotFoundError(f'Offline index missing; run python -m pricing.knowledge rebuild ({database})')
    connection = sqlite3.connect(f'{database.resolve().as_uri()}?mode=ro', uri=True)
    if connection.execute('PRAGMA user_version').fetchone()[0] != DATABASE_VERSION:
        connection.close()
        raise ValueError('Offline index schema changed; run python -m pricing.knowledge rebuild')
    return connection


def _property_clauses(properties, *, minimum=False):
    """Typed JSON predicates: absent or string/bool numeric values never match numbers."""
    clauses, args = [], []
    for key, value in properties.items():
        if not re.fullmatch(r'\d+', str(key)):
            raise ValueError('Property IDs must be numeric IDs from the local dictionary')
        path = f'$.properties."{key}"'
        numeric = type(value) in (int, float) and math.isfinite(value)
        if minimum and not numeric:
            raise ValueError('Minimum property values must be finite numbers')
        if numeric:
            clauses.append(
                "(json_type(e.payload,?) IN ('integer','real') AND json_extract(e.payload,?) "
                + ('>=' if minimum else '=')
                + ' ?)'
            )
            args.extend((path, path, value))
        else:
            encoded = json.dumps(value, allow_nan=False, separators=(',', ':'))
            if value is None:
                raise ValueError('Unknown property values cannot be strict search predicates')
            clauses.append("(json_type(e.payload,?)=json_type(?) AND json_extract(e.payload,?)=json_extract(?,'$'))")
            args.extend((path, encoded, path, encoded))
    return clauses, args


def search(database, query='', *, limit=20, **facets):
    """Find evidence by plain text and exact facets; FTS is discovery, not valuation."""
    invalid = set(facets) - set(FACETS) - {'base_name', 'properties', 'property_min', 'runeword'}
    if invalid:
        raise ValueError(f'Unknown facets: {sorted(invalid)}')
    terms = re.findall(r'\w+', query, flags=re.UNICODE)
    if query.strip() and not terms:
        return []
    where, args = [], []
    tables = 'evidence e'
    ordering = 'e.name,e.kind,e.id'
    if terms:
        tables += ' JOIN evidence_fts f ON f.rowid=e.id'
        where.append('evidence_fts MATCH ?')
        args.append(' AND '.join(f'"{term}"' for term in terms))
        ordering = 'bm25(evidence_fts),e.id'
    for key, value in facets.items():
        if value is not None:
            if key in ('properties', 'property_min'):
                clauses, parameters = _property_clauses(value, minimum=key == 'property_min')
                where.extend(clauses)
                args.extend(parameters)
            elif key == 'base_name':
                where.append(
                    '(e.normalized_name=? OR e.id IN '
                    "(SELECT evidence_id FROM associations WHERE facet='base_name' AND value=?))"
                )
                args.extend((normalize_name(value), normalize_name(value)))
            elif key == 'runeword':
                where.append("lower(json_extract(e.payload,'$.details.runeword'))=?")
                args.append(normalize_name(value))
            elif key == 'rarity':
                where.append(
                    '(e.rarity=? OR (e.rarity IS NULL AND EXISTS '
                    "(SELECT 1 FROM json_each(e.payload,'$.predicates.quality') WHERE value=?)))"
                )
                args.extend((normalize_name(value), normalize_name(value)))
            elif key in ('class', 'build'):
                where.append(
                    'EXISTS (SELECT 1 FROM associations a WHERE a.evidence_id=e.id AND a.facet=? AND a.value=?)'
                )
                args.extend((key, normalize_name(value)))
            else:
                where.append(f'e.{key}=?')
                args.append(value)
    clause = ' WHERE ' + ' AND '.join(where) if where else ''
    with _connect(database) as connection:
        rows = connection.execute(
            f'SELECT e.payload FROM {tables}{clause} ORDER BY {ordering} LIMIT ?',
            (*args, max(1, min(limit, 1000))),
        )
        return [json.loads(row[0]) for row in rows]


def lookup(database, name, *, limit=5, **facets):
    """Return bounded evidence with full-cohort price summaries and visible gaps."""
    invalid = set(facets) - set(FACETS) - {'properties', 'socket_contents'}
    if invalid:
        raise ValueError(f'Unknown facets: {sorted(invalid)}')
    with _connect(database) as connection:
        rows = [
            json.loads(row[0])
            for row in connection.execute(
                'SELECT payload FROM evidence WHERE normalized_name=? OR id IN '
                "(SELECT evidence_id FROM associations WHERE facet IN ('base_name','alias') AND value=?) "
                'ORDER BY kind,id',
                (normalize_name(name), normalize_name(name)),
            )
        ]
    result = {
        'query': name,
        'facets': facets,
        'status': 'known' if rows else 'unknown',
        'price_status': 'unresolved',
        'evidence': {},
        'counts': {},
        'market': None,
        'gaps': [],
        'offline': True,
    }
    if not rows:
        result['gaps'].append('No exact identity evidence; retain for further identification or research.')
        result['candidates'] = [
            {'name': row['name'], 'kind': row['kind']} for row in search(database, name, limit=limit)
        ]
        return result
    market = []
    for row in rows:
        if row['kind'] == 'market':
            market.append(row)
            continue
        if (
            row['kind'] == 'historical_market'
            and row.get('bucket')
            and facets.get('rarity') in ('normal', 'superior', 'low quality', 'low_quality')
            and type(facets.get('ethereal')) is bool
            and facets.get('sockets') is not None
            and facets.get('socket_contents') == 'empty'
        ):
            from pricing.knowledge.bases import bucket_matches

            candidate = {
                **facets,
                'affixes': [
                    {'property_id': key, 'value': value} for key, value in facets.get('properties', {}).items()
                ],
            }
            if not bucket_matches(row['bucket'], candidate):
                continue
        if row['kind'] == 'base_rule':
            rarity = facets.get('rarity')
            if rarity and rarity not in ('normal', 'superior', 'low_quality'):
                continue
            contents = facets.get('properties', {}).get('934')
            if facets.get('socket_contents') == 'filled' or contents:
                continue
        qualities = row.get('predicates', {}).get('quality')
        if isinstance(qualities, list) and facets.get('rarity') and facets['rarity'] not in qualities:
            continue
        if row.get('predicates', {}).get('requires_empty_sockets') and facets.get('socket_contents') == 'filled':
            continue
        # Context remains useful when it does not assert the requested facet.
        # Contradictory explicit recipe/socket facts are never returned as applicable.
        if any(
            _facet_values(row, key)
            and (normalize_name(value) if isinstance(value, str) else value) not in _facet_values(row, key)
            for key, value in facets.items()
            if key != 'properties' and value is not None
        ):
            continue
        kind = row['kind']
        result['counts'][kind] = result['counts'].get(kind, 0) + 1
        section = result['evidence'].setdefault(kind, [])
        if len(section) < limit:
            section.append(row)
    if market:
        from pricing.knowledge.market import summarize

        result['market'] = summarize(market, predicates=facets or None)
        if result['market']['priced_sellers']:
            result['price_status'] = 'comparable_evidence_requires_roll_review' if facets else 'name_level_watch_only'
        else:
            result['gaps'].append('No priced, verified single-unit comparisons match the supplied facets.')
    if not market:
        result['gaps'].append('No normalized market observations; utility and demand are independent of resale value.')
    result['counts']['market_observations'] = len(market)
    from pricing.knowledge.retrieval import item

    prepared = item(database, name)
    if facets.get('rarity'):
        prepared['items'] = [row for row in prepared['items'] if row.get('quality') == facets['rarity']]
        prepared['status'] = 'ambiguous' if len(prepared['items']) > 1 else 'known' if prepared['items'] else 'unknown'
    if prepared['items']:
        result['prepared'] = prepared
    return result


def index_status(database):
    with _connect(database) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='build'").fetchone()[0])


def compact_result(result):
    """Project first-pass evidence; retain locators and disclose omitted fields."""

    def project(row):
        keep = {
            'name',
            'kind',
            'category',
            'rarity',
            'sockets',
            'ethereal',
            'base_code',
            'build',
            'class',
            'side',
            'slot',
            'variant',
            'predicates',
            'source_locator',
            'date',
            'bucket',
            'scope_status',
            'caveat',
            'catalog_id',
            'market_coverage',
            'properties',
            'quality',
            'set_definition',
            'game_definition',
            'tier_pools',
            'range_pools',
            'rare_range_pools',
            'base_definition',
            'base_defense_range',
            'roll_ranges',
            'quality_ranges',
            'roll_tiers',
            'table_id',
            'base_codes',
            'affix_table',
            'runes',
        }
        projected = {key: value for key, value in row.items() if key in keep and value is not None}
        source = row.get('source')
        if isinstance(source, dict):
            projected['source'] = {
                key: value
                for key, value in source.items()
                if key
                in {
                    'path',
                    'url',
                    'fetched_at',
                    'source_date',
                    'source_updated_at',
                }
                and value is not None
            }
        elif source:
            projected['source'] = source
        projected['record'] = {key: row.get('artifact', {}).get(key) for key in ('path', 'locator')}
        details = row.get('details', {})
        if isinstance(details, dict):
            omit = {
                'raw_item',
                'item_definition',
                'properties',
                'raw_properties',
                'related_builds',
                'related_classes',
                'desirable_stats_from_guides',
                'builds',
                'stats',
            }
            if row.get('kind') == 'historical_market':
                retain = {
                    'bucket_def',
                    'roll_bucket',
                    'threshold',
                    'n',
                    'n_priced',
                    'n_sellers',
                    'n_priced_in_runes',
                    'min_ist',
                    'median_ist',
                    'max_ist',
                    'thin',
                    'date',
                    'median_note',
                }
                omit = set(details) - retain
            projected['details'] = {key: value for key, value in details.items() if key not in omit}
            omitted = sorted(set(details) & omit)
            if omitted:
                projected['details_omitted'] = omitted
        return projected

    if isinstance(result, list):
        return [project(row) for row in result]
    result = dict(result)
    result['evidence'] = {kind: [project(row) for row in rows] for kind, rows in result.get('evidence', {}).items()}
    result['more_evidence'] = 'Use --full and --limit N or search with facets; counts include omitted records.'
    return result
