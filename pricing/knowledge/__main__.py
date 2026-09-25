"""Offline appraisal CLI: python -m pricing.knowledge --help."""

import argparse
import json
import sys
from pathlib import Path

from pricing.knowledge.index import build_index, compact_result, index_status, lookup, search


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / 'data' / 'appraisal.sqlite3'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    commands = parser.add_subparsers(dest='command', required=True)
    snapshot = commands.add_parser('snapshot', help='Decode verified ring fields from a saved host probe; offline')
    snapshot.add_argument('directory', type=Path)
    image = commands.add_parser('image', help='EasyOCR image to offline candidate evidence for agent review')
    image.add_argument('image', type=Path)
    image.add_argument('--model-dir', type=Path)
    rebuild = commands.add_parser('rebuild', help='Rebuild local index from portable evidence; no network')
    rebuild.add_argument('--input', action='append', type=Path, dest='inputs')
    commands.add_parser('coverage', help='Show indexed sources and record counts')
    recommendations = commands.add_parser('recommend', help='Prepared offline leveling recommendations')
    recommendations.add_argument('--class', dest='class_name', required=True)
    recommendations.add_argument('--quality', default='unique,set')
    recommendations.add_argument('--purpose', default='leveling')
    recommendations.add_argument('--min-level', type=int, default=1)
    recommendations.add_argument('--max-level', type=int)
    recommendations.add_argument('--archetype', choices=('caster', 'melee', 'general'))
    recommendations.add_argument('--side', choices=('player', 'merc'), default='player')
    recommendations.add_argument('--slot')
    recommendations.add_argument('--limit', type=int, default=12)
    recommendations.add_argument('--offset', type=int, default=0)
    details = commands.add_parser('item', help='Prepared facts by name, alias or stable ID')
    details.add_argument('name')
    details.add_argument('--full', action='store_true')
    properties = commands.add_parser('properties', help='Find observed Traderie property IDs by label')
    properties.add_argument('query', nargs='?', default='')
    sockets = commands.add_parser('sockets', help='Evaluate socket outcomes from portable mechanics')
    sockets.add_argument('name')
    sockets.add_argument('--method', required=True, choices=('drop', 'larzuk', 'cube'))
    sockets.add_argument('--ilvl', type=int)
    sockets.add_argument('--quality', default='normal')
    sockets.add_argument('--current-sockets', type=int, default=0)
    sockets.add_argument('--difficulty', choices=('normal', 'nightmare', 'hell'))
    for operation in ('lookup', 'search'):
        command = commands.add_parser(operation)
        command.add_argument('name', nargs='?', default='')
        command.add_argument('--limit', type=int, default=2 if operation == 'lookup' else 20)
        command.add_argument('--full', action='store_true', help='Include full source and item-definition evidence')
        for facet in ('kind', 'category', 'rarity', 'side', 'class', 'build', 'variant'):
            command.add_argument(f'--{facet}')
        command.add_argument('--sockets', type=int)
        command.add_argument('--ethereal', action=argparse.BooleanOptionalAction, default=None)
        command.add_argument('--property', action='append', default=[], help='Market property ID=JSON value')
        if operation == 'search':
            command.add_argument('--base', dest='base_name', help='Exact base identity, independently of text')
            command.add_argument('--runeword', help='Exact recipe name across bases')
            command.add_argument('--property-min', action='append', default=[], help='Property ID=numeric minimum')
        if operation == 'lookup':
            command.add_argument('--socket-contents', choices=('empty', 'filled', 'unknown'))
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    database = args.pop('database')
    output_indent = 2
    try:
        if command == 'snapshot':
            from inventory_tracking.items.decode import decode_rings
            from pricing.knowledge.pipeline import retrieve_draft

            directory = args['directory']
            observations = decode_rings(
                json.loads((directory / 'units.json').read_text()),
                json.loads((directory / 'report.json').read_text()),
            )
            result = [retrieve_draft(row, database) for row in observations]
        elif command == 'image':
            from pricing.knowledge.pipeline import extract_and_retrieve

            result = extract_and_retrieve(args['image'], database, model_dir=args['model_dir'])
        elif command == 'rebuild':
            paths = args['inputs'] or [
                ROOT / 'data' / filename
                for filename in (
                    'appraisal-catalog.json',
                    'appraisal-trade-catalog.json',
                    'appraisal-demand.json',
                    'appraisal-utility.json',
                    'appraisal-legacy.json',
                    'appraisal-value-watch.json',
                    'appraisal-market.jsonl',
                    'appraisal-item-facts.json',
                    'appraisal-definitions.json',
                    'appraisal-runewords.json',
                    'appraisal-recommendations.json',
                )
            ]
            result = build_index(paths, database)
        elif command in ('recommend', 'item'):
            from pricing.knowledge.retrieval import item, recommend

            result = (recommend if command == 'recommend' else item)(database, **args)
            output_indent = None
        elif command == 'coverage':
            result = index_status(database)
        elif command == 'properties':
            data = json.loads((ROOT / 'data' / 'appraisal-properties.json').read_text())
            query = args['query'].casefold()
            result = [row for row in data['properties'].values() if query in json.dumps(row).casefold()]
        elif command == 'sockets':
            from pricing.knowledge.utility import socket_options_from_row

            name = args.pop('name')
            evidence = lookup(database, name, limit=1000)['evidence'].get('base_rule', [])
            row = next((row for row in evidence if row.get('details', {}).get('rule') == 'socket_potential'), None)
            if row is None:
                raise ValueError(f'No verified portable socket mechanics for {name}')
            result = {
                'name': name,
                **socket_options_from_row(row, **args),
                'source': row.get('source'),
                'offline': True,
            }
        else:
            name = args.pop('name')
            limit = args.pop('limit')
            full = args.pop('full')
            properties = dict(part.split('=', 1) for part in args.pop('property'))
            minimums = dict(part.split('=', 1) for part in args.pop('property_min', []))
            facets = {key: value for key, value in args.items() if value is not None}
            if properties:
                facets['properties'] = {key: json.loads(value) for key, value in properties.items()}
            if minimums:
                facets['property_min'] = {key: json.loads(value) for key, value in minimums.items()}
            operation = lookup if command == 'lookup' else search
            result = operation(database, name, limit=limit, **facets)
            if not full:
                result = compact_result(result)
                output_indent = None
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=output_indent,
                **({'separators': (',', ':')} if command in ('recommend', 'item') else {}),
            )
        )
    except (OSError, ValueError, ImportError, RuntimeError) as error:
        print(json.dumps({'error': str(error), 'offline': True}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
