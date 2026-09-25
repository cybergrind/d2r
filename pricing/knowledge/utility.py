"""Source-preserving leveling inventory and independently derived recipe compatibility.

This adapter never fetches during a lookup. Run as a module to rebuild its portable artifact.
"""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


CLASSES = ('amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock')
GUIDES = {name: name for name in CLASSES} | {
    'amazon': 'amazon-leveling-guide',
    'warlock': 'abyss-warlock-leveling-build-guide',
}


def type_closure(item_type, types):
    """Walk both equivalence parents; malformed cycles cannot loop forever."""
    found, pending = set(), [item_type]
    while pending:
        current = pending.pop()
        if not current or current in found:
            continue
        found.add(current)
        entry = types.get(current, {})
        pending.extend(entry.get(key) for key in ('equiv1', 'equiv2'))
    return found


def cube_outcomes(caps):
    """Six equally likely rolls clamped to the item-level socket cap.

    Source: cached Maxroll items/sockets, Socketing Base Items probability tables.
    Separate caps remain conditional alternatives, never equally weighted levels.
    """
    return [
        {
            'maximum': cap,
            'denominator': 6,
            'weights': {count: 1 if count < cap else 7 - cap for count in range(1, cap + 1)},
        }
        for cap in sorted(set(caps))
        if type(cap) is int and 1 <= cap <= 6
    ]


def socket_options(base, types, *, method, ilvl=None, quality='normal', current_sockets=0, difficulty=None):
    """Describe possibilities, never infer an unknown item level or reduce sockets."""
    if method not in {'cube', 'larzuk', 'drop'}:
        raise ValueError('Unknown socket method')
    if current_sockets:
        return {
            'eligible': False,
            'conditional': False,
            'possible_sockets': [current_sockets],
            'reason': 'Existing socket count cannot be changed by adding sockets',
        }
    if method == 'cube' and quality != 'normal':
        return {
            'eligible': False,
            'conditional': False,
            'possible_sockets': [],
            'reason': 'Ordinary cube socketing requires normal quality (ethereal is permitted)',
        }
    if quality not in {'normal', 'superior', 'low_quality'}:
        return {
            'eligible': False,
            'conditional': False,
            'possible_sockets': [],
            'reason': 'This API covers nonmagical runeword bases only',
        }
    record = types.get(base.get('type'), {})
    cap = base.get('gemsockets', 0)
    brackets = [min(cap, record.get(key, 0)) for key in ('maxsock1', 'maxsock25', 'maxsock40')]
    caps = brackets if ilvl is None else [brackets[0 if ilvl <= 25 else 1 if ilvl <= 40 else 2]]
    if method == 'drop':
        if difficulty not in {'normal', 'nightmare', 'hell'}:
            return {
                'eligible': False,
                'conditional': True,
                'possible_sockets': [],
                'reason': 'Natural drops require difficulty information',
            }
        caps = [min(n, {'normal': 3, 'nightmare': 4, 'hell': 6}[difficulty]) for n in caps]
    values = sorted(set(caps)) if method == 'larzuk' else list(range(1, max(caps, default=0) + 1))
    return {
        'eligible': bool(cap),
        'conditional': ilvl is None,
        'possible_sockets': values if cap else [],
        **({'cube_outcomes': cube_outcomes(caps)} if method == 'cube' else {}),
        'maximum_by_ilvl_bracket': brackets,
        'reason': 'Maximum depends on item level' if ilvl is None else 'Known item level',
    }


def _translated(strings, key, fallback=None):
    value = strings.get(key, fallback or key)
    return value.strip() if isinstance(value, str) else fallback or key


def legal_recipe_edges(game, strings):
    """Derive type/capacity edges from game records, not recommended-base prose.

    Mode availability remains a separate unknown when the source omits those flags.
    """
    rows = []
    for recipe_id, recipe in game['runes'].items():
        rune_codes = [recipe[f'rune{i}'] for i in range(1, 7) if recipe.get(f'rune{i}')]
        if not rune_codes:
            continue
        allowed = {value for key, value in recipe.items() if re.fullmatch(r'itype\d+', key)}
        excluded = {value for key, value in recipe.items() if re.fullmatch(r'etype\d+', key)}
        for category in ('armor', 'weapons'):
            for code, base in game[category].items():
                ancestry = type_closure(base.get('type'), game['itemTypes'])
                if not (ancestry & allowed) or ancestry & excluded or base.get('gemsockets', 0) < len(rune_codes):
                    continue
                rows.append(
                    {
                        'name': _translated(strings, base.get('namestr', code), base['name']),
                        'kind': 'base_rule',
                        'category': category,
                        'base_code': code,
                        'sockets': len(rune_codes),
                        'source_id': 'maxroll-game-data',
                        'source_locator': f'runes/{recipe_id};{category}/{code}',
                        'predicates': {
                            'quality': ['normal', 'superior', 'low_quality'],
                            'exact_sockets': len(rune_codes),
                            'requires_empty_sockets': True,
                            'rune_order_required': True,
                            'mode_availability_requires_verification': True,
                        },
                        'details': {
                            'runeword': _translated(strings, recipe['name']),
                            'recipe_id': recipe_id,
                            'rune_codes': rune_codes,
                            'legality': 'verified_type_and_capacity',
                            'mode_availability': 'not_encoded_by_source',
                            'recommended': False,
                            'base_type': base.get('type'),
                            'allowed_types': sorted(allowed),
                            'base_maximum_sockets': base.get('gemsockets'),
                            'socket_options': socket_options(base, game['itemTypes'], method='larzuk'),
                            'ethereal': 'does_not_change_recipe_type_compatibility',
                            'staffmods': 'preserved_base_properties; not required for legal recipe',
                        },
                    }
                )
    return rows


def transcript_rows(data):
    rows = []
    for entry in data['items']:
        predicates = {}
        if entry['name'] == "Death's Hand":
            predicates['requires_items'] = ["Death's Guard"]
        if entry['name'].startswith("Sigon's"):
            predicates['set_bonus_requires_other_pieces'] = True
        rows.append(
            {
                'name': entry['name'],
                'kind': 'leveling',
                'category': entry['item_kind'],
                'source_id': 'mrllamasc-transcript',
                'source_locator': entry['source_timestamp'],
                'predicates': predicates,
                'details': entry,
            }
        )
    for entry in data['generic_patterns']:
        rows.append(
            {
                'name': entry['name'],
                'kind': 'keep_pattern',
                'source_id': 'mrllamasc-transcript',
                'source_locator': entry['source_timestamp'],
                'predicates': {'slots': entry['slots']},
                'details': entry,
            }
        )
    for entry in data['negative_or_scope_mentions']:
        rows.append(
            {
                'name': entry['name'],
                'kind': 'leveling',
                'source_id': 'mrllamasc-transcript',
                'source_locator': entry['timestamp'],
                'predicates': {},
                'details': entry | {'excluded_context': True, 'keep_recommendation': False},
            }
        )
    return rows, {
        'named_candidates': len(data['items']),
        'patterns': len(data['generic_patterns']),
        'excluded_context': len(data['negative_or_scope_mentions']),
    }


class GuideItems(HTMLParser):
    """Capture explicit item markup and its nearest heading, not navigation names."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.entries = []
        self.heading = 'introduction'
        self.heading_text = None
        self.capture = None
        self.planners = set()
        self.headings = []
        self.checklists = []
        self.checklist = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'br', 'img', 'meta', 'link', 'input', 'hr', 'source', 'wbr'}:
            self.handle_data(' ')
            return
        self.stack.append(tag)
        if attrs.get('data-d2planner-profile'):
            self.planners.add(attrs['data-d2planner-profile'])
        if tag == 'tr' and 'gear' in self.heading:
            self.checklist = {'text': [], 'heading': self.heading}
        if tag in {'h2', 'h3', 'h4'}:
            self.heading_text = []
            self.heading = attrs.get('id', self.heading)
        classes = attrs.get('class', '').split()
        if re.fullmatch(r'[a-z0-9]{8}', attrs.get('data-d2-id', '')):
            self.planners.add(attrs['data-d2-id'])
        if self.capture is None and ('d2planner-item' in classes or 'd2-item' in classes):
            self.capture = {
                'depth': len(self.stack),
                'text': [],
                'id': attrs.get('data-d2-id'),
                'heading': self.heading,
                'offset': self.getpos(),
            }

    def handle_endtag(self, tag):
        if tag == 'tr' and self.checklist is not None:
            self.checklist['text'] = ' '.join(self.checklist['text']).strip()
            self.checklists.append(self.checklist)
            self.checklist = None
        if self.capture and len(self.stack) == self.capture['depth']:
            record = self.capture
            record['text'] = ''.join(record['text']).strip()
            self.entries.append(record)
            self.capture = None
        if tag in {'h2', 'h3', 'h4'} and self.heading_text is not None:
            self.headings.append({'id': self.heading, 'title': ''.join(self.heading_text).strip()})
            self.heading_text = None
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_data(self, text):
        if self.checklist is not None:
            self.checklist['text'].append(text)
        if self.capture is not None:
            self.capture['text'].append(text)
        if self.heading_text is not None:
            self.heading_text.append(text)


def _source(root, relative, source_id, url=None, date=None):
    path = root / relative
    if date is None and path.suffix == '.html':
        matched = re.search(r'"dateModified":"([^"]+)"', path.read_text())
        date = matched.group(1) if matched else None
    return {
        'id': source_id,
        'path': relative,
        'url': url,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_date': date,
        'fetched_at': None,
        'parser_version': 1,
    }


def build_utility(root):
    from pricing.knowledge.builds import load_catalog, planner_rows

    raw = root / 'pricing/raw/mr'
    game = json.loads((raw / 'planners/game-data.json').read_text())
    strings = {v[0]: v[1] for v in json.loads((raw / 'planners/game-strings.json').read_text()) if v}
    # Current d2data supplies RotW additions and complete/enabled recipe information.
    current = root / 'pricing/raw/d2data'
    for group in ('weapons', 'armor', 'misc'):
        game[group] = json.loads((current / f'{group}.json').read_text())
    game['runes'] = {
        name: {key.lower(): value for key, value in row.items()} | {'name': name}
        for name, row in json.loads((current / 'runes.json').read_text()).items()
        if row.get('complete')
    }
    game['itemTypes'] = {
        code: {key.lower(): value for key, value in row.items()}
        | {
            'maxsock1': row.get('MaxSockets1', 0),
            'maxsock25': row.get('MaxSockets2', 0),
            'maxsock40': row.get('MaxSockets3', 0),
        }
        for code, row in json.loads((current / 'itemtypes.json').read_text()).items()
    }
    catalog = load_catalog(root)
    transcript = json.loads((root / 'pricing/data/appraisal-leveling-candidates-2026-09-23.json').read_text())
    rows, transcript_coverage = transcript_rows(transcript)
    by_name = {re.sub(r'[^a-z0-9]', '', item['name'].lower()): item for item in catalog.values()}
    for row in rows:
        identity = by_name.get(re.sub(r'[^a-z0-9]', '', row['name'].lower()))
        if identity:
            row['details']['canonical_identity'] = identity
            row['details']['identity_status'] = 'catalog_matched'
        elif row['kind'] == 'leveling':
            row['details']['identity_status'] = 'unresolved'
    transcript_coverage['catalog_matched_named'] = sum(
        row['kind'] == 'leveling'
        and not row['details'].get('excluded_context')
        and row['details'].get('identity_status') == 'catalog_matched'
        for row in rows
    )
    sources = [
        _source(root, transcript['transcript_path'], 'mrllamasc-transcript', transcript['source']['url'], '2025-04-24'),
        _source(root, 'pricing/raw/mr/planners/game-data.json', 'maxroll-game-data'),
        _source(root, 'pricing/raw/mr/planners/game-strings.json', 'maxroll-game-strings'),
        _source(
            root,
            'pricing/raw/mr/leveling/sockets.html',
            'maxroll-sockets',
            'https://maxroll.gg/d2/items/sockets',
            '2026-06-16',
        ),
    ]
    sources[0]['parsed_sections'] = ['00:00-46:53']
    sources[1]['parsed_sections'] = ['armor', 'weapons', 'runes', 'itemTypes']
    sources[2]['parsed_sections'] = ['localized item names']
    sources[3]['parsed_sections'] = ['Item Generation', 'Horadric Cube Recipes', 'Number of Sockets by ilvl']
    for group in ('weapons', 'armor', 'misc', 'runes', 'itemtypes'):
        source = _source(
            root,
            f'pricing/raw/d2data/{group}.json',
            f'd2data-{group}',
            f'https://raw.githubusercontent.com/blizzhackers/d2data/master/json/{group}.json',
        )
        source['parsed_sections'] = [group]
        sources.append(source)
    class_coverage = {}
    for class_name, slug in GUIDES.items():
        path = raw / 'leveling' / f'{slug}.html'
        parser = GuideItems()
        html = path.read_text()
        parser.feed(html)
        source_id = f'leveling-{class_name}'
        source = _source(root, str(path.relative_to(root)), source_id, f'https://maxroll.gg/d2/guides/{slug}')
        source['parsed_sections'] = parser.headings
        sources.append(source)
        for n, entry in enumerate(parser.entries):
            identity = (entry['id'] or '').split('-')[0]
            resolved = catalog.get(identity)
            name = resolved['name'] if resolved else entry['text'] or entry['id']
            line, col = entry['offset']
            position = sum(len(part) for part in html.splitlines(keepends=True)[: line - 1]) + col
            context = unescape(re.sub(r'<[^>]+>', ' ', html[max(0, position - 300) : position + 800]))
            if not name:
                continue
            rows.append(
                {
                    'name': name,
                    'kind': 'leveling',
                    'class': class_name,
                    'source_id': source_id,
                    'source_locator': f'{entry["heading"]}/item/{n}@{entry["offset"]}',
                    'predicates': {'stage': entry['heading']},
                    'details': {
                        'original_label': entry['text'],
                        'source_item_id': entry['id'],
                        'identity_status': 'source_label',
                        'utility': 'guide_item_mention',
                        'requires_context': True,
                        'context_excerpt': ' '.join(context.split()),
                    },
                }
            )
        for n, checklist in enumerate(parser.checklists):
            if checklist['text'] == 'Item Where Note':
                continue
            rows.append(
                {
                    'name': checklist['text'][:140],
                    'kind': 'keep_pattern',
                    'class': class_name,
                    'source_id': source_id,
                    'source_locator': f'{checklist["heading"]}/checklist/{n}',
                    'predicates': {'stage': checklist['heading']},
                    'details': checklist,
                }
            )
        planners = []
        for ident in sorted(parser.planners):
            relative = f'pricing/raw/mr/leveling/{ident}.json'
            planner_id = f'leveling-planner-{class_name}-{ident}'
            source = _source(root, relative, planner_id, f'https://planners.maxroll.gg/profiles/d2/{ident}')
            doc = json.loads((root / relative).read_text())
            try:
                decoded_rows, covered = planner_rows(doc, catalog, planner_id, slug, class_name)
            except (ValueError, TypeError, AttributeError) as exc:
                source['parsed_sections'] = []
                source['parse_status'] = 'unavailable'
                sources.append(source)
                planners.append({'id': ident, 'status': 'unavailable', 'reason': str(exc)})
                continue
            source['parsed_sections'] = covered
            sources.append(source)
            for row in decoded_rows:
                row = dict(row)
                row['kind'] = 'leveling'
                rows.append(row)
            planners.append({'id': ident, 'coverage': covered, 'rows': len(decoded_rows)})
        class_coverage[class_name] = {
            'guide_status': 'parsed',
            'guide_item_mentions': len(parser.entries),
            'sections': parser.headings,
            'planners': planners,
            'mercenary_status': 'planner_and_guide_context_preserved',
        }
    # Store socket mechanics independently of finished recipe edges so 0os queries work.
    for category in ('armor', 'weapons'):
        for code, base in game[category].items():
            if not base.get('gemsockets'):
                continue
            types = game['itemTypes'].get(base.get('type'), {})
            rows.append(
                {
                    'name': _translated(strings, base.get('namestr', code), base['name']),
                    'kind': 'base_rule',
                    'category': category,
                    'base_code': code,
                    'source_id': f'd2data-{category}',
                    'source_locator': code,
                    'predicates': {'quality': ['normal', 'superior', 'low_quality']},
                    'details': {
                        'rule': 'socket_potential',
                        'socket_mechanics': {
                            'base': {'gemsockets': base['gemsockets'], 'type': base.get('type')},
                            'item_type': {key: types.get(key, 0) for key in ('maxsock1', 'maxsock25', 'maxsock40')},
                            'ordinary_cube_quality': ['normal'],
                            'ethereal_allowed': True,
                            'drop_difficulty_caps': {'normal': 3, 'nightmare': 4, 'hell': 6},
                            'existing_socket_count_immutable': True,
                        },
                        'mechanics_sources': [f'd2data-{category}', 'd2data-itemtypes', 'maxroll-sockets'],
                        'requirements': {key: base.get(key) for key in ('levelreq', 'reqstr', 'reqdex')},
                        'larzuk_unknown_ilvl': socket_options(base, game['itemTypes'], method='larzuk'),
                    },
                }
            )
    # Supplemental source utility: Enchant leveling and mercenary mechanics/examples.
    general_path = 'pricing/raw/mr/resources__general-leveling.html'
    source = _source(
        root, general_path, 'general-leveling', 'https://maxroll.gg/d2/resources/general-leveling', '2026-02-11'
    )
    source['parsed_sections'] = ['Enchantress Leveling', 'Level 20 to 24/25']
    sources.append(source)
    for candidate in transcript['additional_existing_source_candidates']:
        rows.append(
            {
                'name': candidate['name'],
                'kind': 'leveling',
                'source_id': 'general-leveling',
                'source_locator': 'Enchantress Leveling' if candidate['name'] == 'Raven Claw' else 'Level 20 to 24/25',
                'predicates': {'requires_strategy': 'Enchant support'}
                if candidate['name'] == 'Raven Claw'
                else {'drop_provenance': 'Normal Cow Level'},
                'details': candidate,
            }
        )
    merc_path = 'pricing/raw/mr/leveling/mercenary-mechanics.html'
    merc_parser = GuideItems()
    merc_parser.feed((root / merc_path).read_text())
    source = _source(root, merc_path, 'mercenary-mechanics', 'https://maxroll.gg/d2/resources/mercenary-mechanics')
    source['parsed_sections'] = merc_parser.headings
    sources.append(source)
    for n, entry in enumerate(merc_parser.entries):
        identity = (entry['id'] or '').split('-')[0]
        resolved = catalog.get(identity)
        name = resolved['name'] if resolved else entry['text'] or entry['id']
        if name:
            rows.append(
                {
                    'name': name,
                    'kind': 'leveling',
                    'side': 'merc',
                    'source_id': 'mercenary-mechanics',
                    'source_locator': f'{entry["heading"]}/item/{n}',
                    'predicates': {'requires_context': True},
                    'details': {
                        'context': 'Mercenary mechanics/example; not automatically an early-level keep',
                        'source_entry': entry,
                    },
                }
            )
    merc_coverage = []
    for ident in sorted(merc_parser.planners):
        relative = f'pricing/raw/mr/leveling/{ident}.json'
        source_id = f'mercenary-planner-{ident}'
        source = _source(root, relative, source_id, f'https://planners.maxroll.gg/profiles/d2/{ident}')
        doc = json.loads((root / relative).read_text())
        decoded, covered = planner_rows(doc, catalog, source_id, 'mercenary-mechanics', 'all')
        source['parsed_sections'] = covered
        sources.append(source)
        for row in decoded:
            row['kind'] = 'leveling'
            row['details']['requires_context'] = True
            rows.append(row)
        merc_coverage.append({'id': ident, 'rows': len(decoded), 'coverage': covered})
    edges = legal_recipe_edges(game, strings)
    for edge in edges:
        edge['source_id'] = 'd2data-runes'
        edge['details']['mechanics_sources'] = [
            'd2data-runes',
            'd2data-itemtypes',
            f'd2data-{edge["category"]}',
            'maxroll-sockets',
        ]
    rows.extend(edges)
    for ident, recipe in game['runes'].items():
        rune_codes = [recipe[f'rune{i}'] for i in range(1, 7) if recipe.get(f'rune{i}')]
        rows.append(
            {
                'name': _translated(strings, recipe['name']),
                'kind': 'runeword',
                'source_id': 'd2data-runes',
                'source_locator': f'runes/{ident}',
                'sockets': len(rune_codes),
                'details': {
                    'recipe_id': ident,
                    'rune_codes': rune_codes,
                    'runes': [
                        _translated(strings, game.get('misc', {}).get(c, {}).get('namestr', c), c) for c in rune_codes
                    ],
                    'raw_recipe': recipe,
                    'mode_availability': 'not_encoded_by_source',
                },
            }
        )
    # Recommendations remain distinct from legality derived above.
    rec_path = 'pricing/data/wp-a-bases.json'
    sources.append(_source(root, rec_path, 'recommended-bases', date='2026-09-18'))
    for name, rec in json.loads((root / rec_path).read_text()).items():
        for word, count in rec.get('sockets_by_runeword', {}).items():
            rows.append(
                {
                    'name': name,
                    'kind': 'base_rule',
                    'sockets': count,
                    'source_id': 'recommended-bases',
                    'predicates': {
                        'quality': ['normal', 'superior', 'low_quality'],
                        'exact_sockets': count,
                        'requires_empty_sockets': True,
                        'rune_order_required': True,
                        'mode_availability_requires_verification': True,
                    },
                    'source_locator': f'{name}/sockets_by_runeword/{word}',
                    'details': {
                        'runeword': word,
                        'recommended': True,
                        'legality': 'recommendation_only',
                        'context': rec,
                    },
                }
            )
    for source_id, filename, url in [
        (
            'blizzard-season15',
            'blizzard-season15.html',
            'https://news.blizzard.com/en-gb/article/24296140/diablo-ii-resurrected-ladder-season-15-now-live',
        ),
        (
            'blizzard-311',
            'blizzard-311.html',
            'https://news.blizzard.com/en-gb/article/24244884/reign-of-the-warlock-3-1-1-patch-notes',
        ),
    ]:
        source = _source(root, f'pricing/raw/mr/leveling/{filename}', source_id, url)
        source['parsed_sections'] = ['Items' if source_id.endswith('15') else 'Bug Fixes']
        sources.append(source)
    promoted = {'Mania', 'Hysteria', 'Metamorphosis', 'Ground', 'Temper', 'Hearth', 'Cure', 'Bulwark'}
    for row in rows:
        details = row.get('details', {})
        word = details.get('runeword') if row['kind'] == 'base_rule' else row['name']
        if word in promoted or word == 'Mosaic':
            details['mode_availability'] = 'nonladder_rotw_documented'
            row.setdefault('predicates', {})['mode_availability_requires_verification'] = False
            details['mode_source'] = 'blizzard-311' if word == 'Mosaic' else 'blizzard-season15'
            details['mode_note'] = 'Historical NL version; changed Ladder-only stats must not be substituted.'
    for class_name, covered in class_coverage.items():
        class_rows = [row for row in rows if row.get('class') == class_name]
        covered['mercenary_occurrences'] = sum(row.get('side') == 'merc' for row in class_rows)
        covered['unresolved_planner_occurrences'] = sum(
            row.get('details', {}).get('resolution_status') == 'unresolved' for row in class_rows
        )
    return {
        'schema_version': 1,
        'generated_at': datetime.now(UTC).isoformat(),
        'sources': sources,
        'rows': rows,
        'coverage': {
            'classes': class_coverage,
            'transcript': transcript_coverage,
            'recipe_records': len(game['runes']),
            'legal_type_capacity_edges': len(edges),
            'mercenary_planners': merc_coverage,
            'limitations': [
                'Nine recipes have patch-documented NL availability; others retain unknown mode.',
                'Guide prose item mentions require local section context.',
            ],
        },
    }


def socket_options_from_row(row, **facets):
    """Evaluate portable evidence without loading raw cache or reaching the network."""
    mechanics = row['details']['socket_mechanics']
    base = mechanics['base']
    return socket_options(base, {base['type']: mechanics['item_type']}, **facets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, default=Path('pricing/data/appraisal-utility.json'))
    args = parser.parse_args()
    result = build_utility(args.root.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['coverage'], indent=2))


if __name__ == '__main__':
    main()
