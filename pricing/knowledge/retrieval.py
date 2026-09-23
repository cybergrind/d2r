"""Prepared, source-backed item facts and leveling recommendations; strictly local."""

import hashlib
import json


CLASSES = ('amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock')
CLASS_ALIASES = {
    'sorc': 'sorceress',
    'necro': 'necromancer',
    'barb': 'barbarian',
    'pally': 'paladin',
    'sin': 'assassin',
    'zon': 'amazon',
}
QUALITY_ALIASES = {'uniq': 'unique', 'uniques': 'unique', 'sets': 'set'}
ARCHETYPES = ('caster', 'melee', 'general')


def _name(value):
    from pricing.knowledge.index import normalize_name

    return normalize_name(value)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def publish(connection, rows):
    """Materialize facts and reviewed uses as part of the atomic index rebuild."""
    connection.executescript("""
        CREATE TABLE item_facts (
            item_id TEXT PRIMARY KEY, name TEXT NOT NULL, quality TEXT, slot TEXT,
            level INTEGER, summary TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE INDEX item_eligibility ON item_facts(quality,level,slot,item_id);
        CREATE TABLE item_aliases (alias TEXT, item_id TEXT, PRIMARY KEY(alias,item_id));
        CREATE TABLE item_uses (
            id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, class TEXT NOT NULL,
            side TEXT NOT NULL, purpose TEXT NOT NULL, archetype TEXT NOT NULL,
            rank INTEGER NOT NULL, payload TEXT NOT NULL
        );
        CREATE INDEX use_context ON item_uses(class,side,purpose,archetype,item_id);
        CREATE INDEX use_item ON item_uses(item_id);
    """)
    facts = {}
    for row in rows:
        if row['kind'] != 'item_fact':
            continue
        identity = row['item_id']
        if identity in facts:
            raise ValueError(f'Duplicate item fact: {identity}')
        facts[identity] = row
        summary = {
            key: row.get(key)
            for key in ('item_id', 'name', 'quality', 'base_name', 'item_type', 'slot', 'requirements')
        }
        summary['stats'] = [
            {
                'stat': stat.get('label') or stat['property'],
                'value': stat.get('min') if stat.get('min') == stat.get('max') else [stat.get('min'), stat.get('max')],
                **({'parameter': stat['param']} if stat.get('param') is not None else {}),
            }
            for stat in row.get('stats', [])
            if stat.get('label')
        ]
        summary['stats_omitted'] = len(row.get('stats', [])) - len(summary['stats'])
        summary['requirement_scope'] = row.get('requirement_scope')
        summary['gaps'] = row.get('gaps', [])
        summary['availability'] = row.get('availability', 'unverified')
        summary['conditions'] = row.get('conditions', [])
        summary['reference'] = row['artifact']
        level = (row.get('requirements') or {}).get('level')
        if level is not None and (type(level) is not int or not 0 <= level <= 99):
            raise ValueError(f'Invalid equip level for {identity}: {level}')
        connection.execute(
            'INSERT INTO item_facts VALUES (?,?,?,?,?,?,?)',
            (
                identity,
                row['name'],
                row.get('quality'),
                _name(row.get('slot') or ''),
                level,
                _json(summary),
                _json(row),
            ),
        )
        aliases = {identity, row['name'], *row.get('aliases', [])}
        connection.executemany(
            'INSERT OR IGNORE INTO item_aliases VALUES (?,?)', [(_name(a), identity) for a in aliases]
        )
    unresolved = []
    eligible = 0
    for row in rows:
        if row['kind'] != 'recommendation' or row.get('intent') != 'recommend':
            continue
        identity = row.get('item_id')
        if identity not in facts:
            unresolved.append({'name': row['name'], 'item_id': identity})
            continue
        classes = row.get('classes', [])
        archetypes = row.get('archetypes', ['general'])
        side = row.get('side', 'player')
        if not classes or not archetypes or side not in ('player', 'merc'):
            raise ValueError(f'Invalid recommendation context: {row["name"]}')
        strength = row.get('evidence_strength', 'reviewed_inference')
        priority = row.get('priority', 3)
        if type(priority) is not int or not 1 <= priority <= 5:
            raise ValueError(f'Invalid priority: {priority}')
        rank = (6 - priority) * 10 + (2 if strength == 'explicit' else 1)
        use = {key: row.get(key) for key in ('reason', 'conditions', 'benefits', 'evidence_strength', 'archetypes')}
        use['reference'] = row['artifact']
        use['classes'] = classes
        use['side'] = side
        use['purpose'] = row.get('purpose', 'leveling')
        source = row.get('source')
        if isinstance(source, dict):
            use['origin'] = {
                **source,
                'locator': row.get('source_locator'),
                'source_date': row.get('source_date') or source.get('source_date'),
            }
        for class_name in set(classes):
            class_name = _name(class_name)
            if class_name not in CLASSES:
                raise ValueError(f'Unknown recommendation class: {class_name}')
            for archetype in set(archetypes):
                if archetype not in ARCHETYPES:
                    raise ValueError(f'Unknown archetype: {archetype}')
                connection.execute(
                    'INSERT INTO item_uses VALUES (NULL,?,?,?,?,?,?,?)',
                    (
                        identity,
                        class_name,
                        side,
                        row.get('purpose', 'leveling'),
                        archetype,
                        rank,
                        _json(use),
                    ),
                )
        eligible += 1
    report = {
        'facts': len(facts),
        'recommendations': eligible,
        'unresolved_recommendations': unresolved,
        'version': hashlib.sha256(_json([row['artifact'] for row in rows]).encode()).hexdigest(),
    }
    connection.execute('INSERT INTO metadata VALUES (?,?)', ('retrieval', _json(report)))
    return report


def _connect(database):
    from pricing.knowledge.index import _connect as connect

    return connect(database)


def _reference(artifact, sources):
    """Short stable references into portable artifacts, with paths shared once."""
    signature = (artifact.get('path'), artifact.get('sha256'))
    source_id = next((key for key, value in sources.items() if (value['path'], value['sha256']) == signature), None)
    if source_id is None:
        source_id = f's{len(sources) + 1}'
        sources[source_id] = {'path': signature[0], 'sha256': signature[1]}
        for key in ('url', 'source_date', 'source_updated_at', 'fetched_at'):
            if artifact.get(key) is not None:
                sources[source_id][key] = artifact[key]
    return {'source': source_id, 'locator': artifact.get('locator')}


def _present(summary, uses, sources, *, context=False):
    summary = dict(summary)
    reference = _reference(summary.pop('reference'), sources)
    summary['references'] = [reference]
    grouped = {}
    for use in uses:
        use = dict(use)
        ref = _reference(use.pop('reference'), sources)
        origin = use.pop('origin', None)
        if origin:
            use['source'] = _reference(origin, sources)
        if not context:
            for field in ('classes', 'side', 'purpose'):
                use.pop(field, None)
        key = _json(use)
        if key not in grouped:
            grouped[key] = use
            use['references'] = []
        if ref not in grouped[key]['references']:
            grouped[key]['references'].append(ref)
    summary['uses'] = list(grouped.values())
    return summary


def _query_context(class_name, quality, min_level, max_level, archetype, side, purpose, limit, offset):
    defaults = []
    if max_level is None:
        max_level = 25
        defaults.append('max_level')
    class_name = CLASS_ALIASES.get(_name(class_name), _name(class_name))
    if class_name not in CLASSES:
        raise ValueError(f'Unknown class: {class_name}; choose {", ".join(CLASSES)}')
    if quality is None:
        quality = 'unique,set'
    qualities = [QUALITY_ALIASES.get(_name(q), _name(q)) for q in quality.split(',')]
    if not qualities or set(qualities) - {'unique', 'set'}:
        raise ValueError('Supported qualities: unique,set')
    if not 1 <= min_level <= max_level <= 99:
        raise ValueError('Equip level range must satisfy 1 <= min <= max <= 99')
    if archetype is not None and archetype not in ARCHETYPES:
        raise ValueError(f'Unknown archetype: {archetype}')
    if side not in ('player', 'merc') or purpose != 'leveling':
        raise ValueError('Supported purpose is leveling; side must be player or merc')
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError('Limit must be 1..100 and offset nonnegative')
    return class_name, sorted(set(qualities)), max_level, defaults


def recommend(
    database,
    *,
    class_name,
    quality=None,
    min_level=1,
    max_level=None,
    archetype=None,
    slot=None,
    side='player',
    purpose='leveling',
    limit=12,
    offset=0,
):
    """Apply hard facets before ranking, without scanning source evidence payloads."""
    class_name, qualities, max_level, defaults = _query_context(
        class_name,
        quality,
        min_level,
        max_level,
        archetype,
        side,
        purpose,
        limit,
        offset,
    )
    if archetype is None and class_name in ('sorceress', 'necromancer'):
        archetype = 'caster'
        defaults.append('archetype')
    clauses = ['u.class=?', 'u.side=?', 'u.purpose=?', f'f.quality IN ({",".join("?" for _ in qualities)})']
    params = [class_name, side, purpose, *qualities]
    if archetype:
        clauses.append("u.archetype IN (?, 'general')")
        params.append(archetype)
    if slot:
        clauses.append('f.slot=?')
        params.append(
            {'gloves': 'hands', 'boots': 'feet', 'belt': 'waist', 'helm': 'head', 'shield': 'offhand'}.get(
                _name(slot), _name(slot)
            )
        )
    base = ' FROM item_uses u JOIN item_facts f ON f.item_id=u.item_id WHERE ' + ' AND '.join(clauses)
    bounded = base + ' AND f.level BETWEEN ? AND ?'
    bounded_params = [*params, min_level, max_level]
    with _connect(database) as connection:
        total = connection.execute('SELECT count(DISTINCT f.item_id)' + bounded, bounded_params).fetchone()[0]
        unknown = connection.execute(
            'SELECT count(DISTINCT f.item_id)' + base + ' AND f.level IS NULL', params
        ).fetchone()[0]
        records = connection.execute(
            'SELECT f.item_id,f.summary'
            + bounded
            + ' GROUP BY f.item_id ORDER BY max(u.archetype=?) DESC,max(u.rank) DESC,'
            'f.level,f.name,f.item_id LIMIT ? OFFSET ?',
            [*bounded_params, archetype or '', limit, offset],
        ).fetchall()
        sources = {}
        items = []
        for identity, summary in records:
            uses = connection.execute(
                'SELECT DISTINCT u.payload' + bounded + ' AND f.item_id=? ORDER BY u.rank DESC,u.id',
                [*bounded_params, identity],
            ).fetchall()
            items.append(_present(json.loads(summary), [json.loads(row[0]) for row in uses], sources))
        coverage = json.loads(connection.execute("SELECT value FROM metadata WHERE key='retrieval'").fetchone()[0])
        adapter_coverage = json.loads(
            connection.execute("SELECT value FROM metadata WHERE key='prepared_coverage'").fetchone()[0]
        )
        class_gaps = []
        named_gaps = 0
        for source_coverage in adapter_coverage.values():
            if 'named' in source_coverage:
                named_gaps += sum(r['status'] == 'gap' for r in source_coverage['named'])
                class_gaps.extend(source_coverage.get('gaps', []))
                context = source_coverage.get('classes', {}).get(class_name, {})
                if context.get('gap'):
                    class_gaps.append(context['gap'])
    result = {
        'query': {
            'class': class_name,
            'quality': qualities,
            'min_level': min_level,
            'max_level': max_level,
            'archetype': archetype,
            'slot': slot,
            'side': side,
            'purpose': purpose,
        },
        'defaults_applied': defaults,
        'items': items,
        'total': total,
        'offset': offset,
        'truncated': offset + len(items) < total,
        'excluded_unknown_level': unknown,
        'sources': sources,
        'coverage': {
            'facts': coverage['facts'],
            'recommendations': coverage['recommendations'],
            'unresolved_recommendations': len(coverage['unresolved_recommendations']),
            'unprepared_named_candidates': named_gaps,
        },
        'gaps': [
            'Reviewed local recommendations are not an exhaustive equipment ranking.',
            'Attribute requirements and companion set pieces must be checked against your character.',
        ],
        'offline': True,
        'data_version': coverage['version'],
        'next_offset': None,
    }
    result['gaps'].extend(dict.fromkeys(class_gaps))
    # Keep complete item entries; disclose truncation rather than dropping prerequisites.
    while len(_json(result).encode()) + 32 > 12 * 1024 and len(result['items']) > 1:
        result['items'].pop()
        result['truncated'] = True
    if len(_json(result).encode()) > 12 * 1024:
        result['gaps'].append('One complete item exceeds the output budget; prerequisites were retained.')
    result['next_offset'] = offset + len(result['items']) if result['truncated'] else None
    return result


def item(database, name, *, full=False):
    """Expand facts by stable ID or alias; never silently choose an ambiguous identity."""
    sources = {}
    with _connect(database) as connection:
        records = connection.execute(
            'SELECT f.summary,f.payload FROM item_facts f JOIN item_aliases a '
            'ON a.item_id=f.item_id WHERE a.alias=? ORDER BY f.item_id',
            (_name(name),),
        ).fetchall()
        items = []
        for summary, payload in records:
            summary = json.loads(summary)
            uses = [
                json.loads(r[0])
                for r in connection.execute(
                    'SELECT DISTINCT payload FROM item_uses WHERE item_id=? ORDER BY rank DESC,id',
                    (summary['item_id'],),
                )
            ]
            row = _present(summary, uses, sources, context=True)
            if full:
                row['facts'] = json.loads(payload)
                row['recommendations'] = [
                    json.loads(r[0])
                    for r in connection.execute(
                        'SELECT DISTINCT payload FROM item_uses WHERE item_id=? ORDER BY payload',
                        (row['item_id'],),
                    )
                ]
            items.append(row)
    return {
        'query': name,
        'status': 'ambiguous' if len(items) > 1 else 'known' if items else 'unknown',
        'items': items,
        'sources': sources,
        'offline': True,
    }
