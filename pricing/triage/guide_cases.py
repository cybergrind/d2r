"""Extract guide obligations without silently dropping prose we cannot execute yet.

The generated case file retains verbatim text and source anchors. Concrete items
and expectations must be transcribed from that evidence, never from engine output.
Run with ``python -m pricing.triage.guide_cases`` to extract and score offline.
"""

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from inventory_tracking.corpus.score import score


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'guides/pricing.html': {2, 3, 6, 7, 8, 9},
    'guides/pricing-primer.html': {2, 3, 4, 5, 6, 8},
    'guides/warlock.html': set(range(8)),
    'guides/pindle-anya.html': {3, 5},
}


def clean(text):
    return ' '.join(text.split())


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        return clean(self.raw_text())

    def raw_text(self):
        return ''.join(child.raw_text() if isinstance(child, Node) else child for child in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def ancestors(self):
        node = self.parent
        while node:
            yield node
            node = node.parent


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in {
            'area',
            'base',
            'br',
            'col',
            'embed',
            'hr',
            'img',
            'input',
            'link',
            'meta',
            'param',
            'source',
            'wbr',
        }:
            self.current = node
        elif tag in {'br', 'hr'}:
            node.children.append(' ')

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def worked_expectation(text):
    """Only unambiguous leading verdicts; alternatives remain in source text."""
    text = text.casefold()
    if re.match(r"(?:non-eth: )?(?:vendor\b|don't buy\b|imbue or vendor\b)", text):
        return ['vendor']
    if text in {'self-use', 'wear'}:
        return ['self']
    # Guide 'list' specifies tradeability, not evidence of fast turnover.
    if re.match(r'list at\b|~\d.*\blist\b', text):
        return ['sell', 'slow']
    return None


def resolve_row(node, spans):
    """Expand HTML row/column spans so variant rows retain their item identity."""
    resolved = {column: text for column, (_, text) in spans.items()}
    following = {column: (left - 1, text) for column, (left, text) in spans.items() if left > 1}
    column = 0
    for cell in node.children:
        if not isinstance(cell, Node) or cell.tag not in {'td', 'th'}:
            continue
        while column in resolved:
            column += 1
        width, height = int(cell.attrs.get('colspan', 1)), int(cell.attrs.get('rowspan', 1))
        for offset in range(width):
            resolved[column + offset] = cell.text()
            if height > 1:
                following[column + offset] = (height - 1, cell.text())
        column += width
    spans.clear()
    spans.update(following)
    return [resolved.get(column, '') for column in range(max(resolved, default=-1) + 1)]


def extract(html, path):
    section, anchor, heading = None, '', ''
    checklist_false_positive = False
    counts, rows = Counter(), []
    table_spans = {}
    for node in Document(html).root.walk():
        if node.tag == 'h2':
            match = re.fullmatch(r's(\d+)', node.attrs.get('id', ''))
            section = int(match[1]) if match else None
        if node.tag in {'h2', 'h3'}:
            anchor, heading = node.attrs.get('id', anchor), node.text()
        ancestors = list(node.ancestors())
        special = next((n.attrs['id'] for n in ancestors if n.attrs.get('id') in {'miss', 'twin'}), None)
        if section not in SOURCES[path] and not (path.endswith('pricing-primer.html') and special):
            continue
        if special == 'miss' and node.tag == 'tr':
            headers = [n.text() for n in node.children if isinstance(n, Node) and n.tag == 'th']
            if headers and headers[0].startswith('looks '):
                checklist_false_positive = headers[0] == 'looks valuable, is not'
        table = next((n for n in ancestors if n.tag == 'table'), None)
        resolved = resolve_row(node, table_spans.setdefault(table, {})) if node.tag == 'tr' else []
        cells = [child.text() for child in node.children if isinstance(child, Node) and child.tag == 'td']
        table_row = node.tag == 'tr' and bool(cells)
        prose_row = node.tag == 'li' and not any(n.tag in {'li', 'tr', 'nav'} for n in ancestors)
        decision = node.tag == 'div' and 'fbox' in node.attrs.get('class', '').split()
        if not (table_row or prose_row or decision):
            continue
        local_anchor = special or (node.attrs.get('id') if decision else None) or anchor
        source = f'{path}#{local_anchor}'
        counts[source] += 1
        kind = 'table'
        if path.endswith('/pricing.html') and section == 8:
            kind = 'worked'
        elif (path.endswith('/pricing.html') and section == 9) or (special == 'miss' and checklist_false_positive):
            kind = 'false_positive'
        context_reason = None
        if any(
            parent.tag == 'details'
            and any(
                isinstance(child, Node)
                and child.tag == 'summary'
                and re.match(r'review log\b', child.text(), re.IGNORECASE)
                for child in parent.children
            )
            for parent in ancestors
        ):
            context_reason = 'Historical review log; current guidance is in the guide body'
        elif path == 'guides/warlock.html' and section == 7 and heading.startswith('7 · Verify in-game'):
            context_reason = 'Explicitly unverified appendix; not an asserted item verdict'
        elif table_row and len(cells) == 1:
            cell = next(child for child in node.children if isinstance(child, Node) and child.tag == 'td')
            bold = [child for child in cell.children if isinstance(child, Node) and child.tag == 'b']
            if int(cell.attrs.get('colspan', 1)) > 1 and len(bold) == 1 and bold[0].text() == cell.text():
                context_reason = 'Full-width bold table group heading; individual rules follow'
        if context_reason:
            kind = 'context'
        rows.append(
            {
                'id': f'{source}:{counts[source]}',
                'source': source,
                'heading': heading,
                'kind': kind,
                **({'context_reason': context_reason} if context_reason else {}),
                'cells': cells,
                'resolved_cells': resolved,
                'description': cells[0] if cells else node.text(),
                'text': node.text(),
                'expected': worked_expectation(cells[-1]) if kind == 'worked' and cells else None,
            }
        )
    return rows


def base_table_examples(case):
    """Transcribe only explicit single-variant keep/sell rows of the base table."""
    from inventory_tracking.items.metadata import metadata

    cells = case.get('resolved_cells', [])
    if case['source'] != 'guides/pindle-anya.html#s5' or len(cells) < 3:
        return None
    if not re.match(r'^(keep|sell)\b', cells[2]):
        return None
    name = cells[0].split(' (')[0]
    base = next((b for b in metadata()['bases'].values() if b['name'] == name), None)
    if base is None:
        return None
    variant = cells[1].split(' (')[0]
    variants = None
    if variant == 'eth 45@ any sockets':
        variants = [f'eth 45@ {sockets}os normal' for sockets in range(base['max_sockets'] + 1)]
    elif trailing := re.fullmatch(r'([0-6])os Superior 45@', variant):
        variants = [f'45@ {trailing[1]}os Superior']
    elif (mixed := re.fullmatch(r'([0-6])os 45@', variant)) and re.search(
        r'\(bimodal: normal .+, Superior 15 ED .+\)', cells[1]
    ):
        variants = [f'45@ {mixed[1]}os normal', f'45@ {mixed[1]}os Superior ≥15 ED']
    if variants is not None:
        return [
            example
            for text in variants
            for example in base_table_examples(case | {'resolved_cells': [cells[0], text, *cells[2:]]})
        ]
    match = re.fullmatch(
        r'(?:(?P<eth>eth) )?(?:(?P<res>45)@ )?(?P<sockets>[0-6])os '
        r'(?:(?P<noneth>non-eth) )?(?P<quality>normal|Superior)'
        r'(?: (?P<ed>≥15|<15) ED)?(?: (?P<bow>\+3))?(?: (?P<tail_noneth>non-eth))?',
        variant,
    )
    if match is None or (match['eth'] and (match['noneth'] or match['tail_noneth'])):
        return None
    superior = match['quality'] == 'Superior'
    eds = [15] if match['ed'] == '≥15' else [5, 14] if match['ed'] == '<15' else [5, 15] if superior else [0]
    examples = []
    for ed in eds:
        stats = {}
        if ed:
            stats.update({'16:0': ed} if base.get('category') == 'armor' else {'17:0': ed, '18:0': ed})
        if match['res']:
            stats.update({f'{stat}:0': 45 for stat in (39, 41, 43, 45)})
        if match['bow']:
            stats['188:0'] = 3
        examples.append(
            {
                'spec': {
                    'base': name,
                    'rarity': 'superior' if superior else 'normal',
                    'ethereal': bool(match['eth']),
                    'sockets': int(match['sockets']),
                    'stats': stats,
                },
                'expected': ['sell', 'slow', 'check', 'self'],
            }
        )
    return examples


def item_from_spec(spec):
    """Build a guide item using the same native identities as captured drops."""
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties
    from pricing.triage.adapters import from_listing

    meta = metadata()
    base = next(b for b in meta['bases'].values() if b['name'] == spec['base'])
    native = spec.get('stats', {})
    projection, properties = market_properties(), {}
    for key, value in native.items():
        stat, parameter = key.split(':')
        prop = projection.get(key)
        if prop is None and parameter == '0':
            prop = meta['stats'].get(stat, {}).get('property_id')
        if prop is not None:
            properties[prop] = value
    if native.get('17:0') is not None and native.get('17:0') == native.get('18:0'):
        properties['510'] = native['17:0']
    properties.update(spec.get('properties', {}))
    rarity = spec['rarity']
    item = from_listing(
        {
            'name': spec.get('name', spec['base']),
            'base_name': spec['base'],
            'base_code': base['code'],
            'category': spec.get('category', {'unique': 'uniques', 'set': 'sets'}.get(rarity, 'base')),
            'rarity': rarity,
            'amount': spec.get('quantity', 1),
            'properties': properties,
            'ethereal': spec['ethereal'],
            'sockets': spec['sockets'],
            'socket_contents': spec.get('socket_contents', 'empty'),
        }
    )
    # Listing omission defaults must not invent guide/capture facts.
    item.update(
        ethereal=spec['ethereal'], sockets=spec['sockets'], native_rolls=native, item_level=spec.get('item_level')
    )
    return item


def evaluate(cases, assess):
    groups, unresolved, results, labels, failures = {}, [], [], {}, []
    context, pickup = [], []
    classifications = dict.fromkeys(('verdict', 'own-use', 'pickup', 'context'), 0)
    for case in cases:
        category = case.get('classification', 'context' if case['kind'] == 'context' else 'verdict')
        classifications[category] += 1
        if category in {'context', 'pickup'}:
            destination = context if category == 'context' else pickup
            destination.append(
                {
                    'id': case['id'],
                    'text': case['text'],
                    'reason': case.get('classification_reason', case.get('context_reason')),
                }
            )
            continue
        kind = category if case['kind'] == 'table' and case.get('classification') else case['kind']
        group = groups.setdefault(kind, {'total': 0, 'evaluated': 0, 'passed': 0})
        group['total'] += 1
        comparison_passed = True
        if case.get('comparisons'):
            # Some guide rows specify relative value, not an absolute verdict.
            # For example, scoped asks can establish a variant premium.
            passed = True
            for index, comparison in enumerate(case['comparisons']):
                outcomes = []
                for side in ('left', 'right'):
                    entry = comparison[side]
                    item = item_from_spec(entry['spec']) if entry.get('spec') else entry['item']
                    validate_native_keys(item, case['id'])
                    outcomes.append(assess(item))
                fields = comparison.get('equal', [])
                ordered = comparison.get('not_greater', [])
                strict = comparison.get('less_than', [])
                if not fields and not ordered and not strict:
                    raise ValueError(f'{case["id"]}: comparison requires fields')
                differences = {
                    field: [outcomes[0][field], outcomes[1][field]]
                    for field in fields
                    if outcomes[0][field] != outcomes[1][field]
                }
                for field in set(ordered) | set(strict):
                    from pricing.triage.roll_comparisons import numeric

                    left, right = (outcome.get(field) for outcome in outcomes)
                    # Missing estimates cannot prove a price discount, even
                    # when both sides lack a supported band.
                    if not numeric(left) or not numeric(right) or left > right or (field in strict and left == right):
                        differences[field] = [left, right]
                if differences:
                    passed = False
                    failures.append({'id': f'{case["id"]}/{index}', 'differences': differences})
            if not any(case.get(key) for key in ('item', 'items', 'spec', 'specs', 'examples')):
                group['evaluated'] += 1
                group['passed'] += passed
                continue
            comparison_passed = passed
        items = case.get('items', []) or ([case['item']] if case.get('item') else [])
        specs = case.get('specs', []) or ([case['spec']] if case.get('spec') else [])
        if specs:
            items = [item_from_spec(spec) for spec in specs]
        expected = [case.get('expected')] * len(items)
        expected_fields = [case.get('expected_fields', {})] * len(items)
        if case.get('examples'):
            items = [item_from_spec(e['spec']) if e.get('spec') else e.get('item') for e in case['examples']]
            expected = [e.get('expected') for e in case['examples']]
            expected_fields = [e.get('expected_fields', {}) for e in case['examples']]
        if not items or not all(items) or not all(expected):
            missing = ([] if items and all(items) else ['item']) + ([] if expected and all(expected) else ['expected'])
            unresolved.append({'id': case['id'], 'missing': missing, 'reason': case.get('unresolved_reason')})
            continue
        if category == 'own-use':
            expected = [['self']] * len(items)
        group['evaluated'] += 1
        passed = comparison_passed
        for index, item in enumerate(items):
            validate_native_keys(item, case['id'])
            result = assess(item)
            fields = expected_fields[index]
            accepted = result['verdict'] in expected[index] and all(
                field in result and result[field] == value for field, value in fields.items()
            )
            passed &= accepted
            identity = case['id'] if len(items) == 1 else f'{case["id"]}/{index}'
            row = result | {'id': identity, 'name': item.get('name', ''), 'rarity': item.get('category', '')}
            results.append(row)
            # Exact-verdict scorer supplements source-row accuracy, not its denominator.
            if len(expected[index]) == 1:
                labels[identity] = expected[index][0]
            if not accepted:
                failure = {'id': identity, 'expected': expected[index], 'actual': result}
                if fields:
                    failure['expected_fields'] = fields
                failures.append(failure)
        group['passed'] += passed
    for group in groups.values():
        group['accuracy'] = group['passed'] / group['total'] if group['total'] else None
    table_score = {
        key: sum(groups.get(kind, {}).get(key, 0) for kind in ('table', 'verdict', 'own-use'))
        for key in ('total', 'evaluated', 'passed')
    }
    table_score['accuracy'] = table_score['passed'] / table_score['total'] if table_score['total'] else None
    return {
        'classifications': classifications,
        'table_score': table_score,
        'pickup': pickup,
        'groups': groups,
        'context': context,
        'unresolved': unresolved,
        'failures': failures,
        'exact_verdict_score': score(results, labels),
    }


def validate_native_keys(item, identity):
    if any(not re.fullmatch(r'\d+:\d+', key) for key in item.get('native_rolls', {})):
        raise ValueError(f'{identity}: native stat keys must include the parameter, as in captures')


def build_cases():
    from pricing.knowledge.refresh import atomic_json

    path = ROOT / 'pricing/triage/guide-cases.json'
    cases = [case for source in SOURCES for case in extract((ROOT / source).read_text(), source)]
    # Keep reviewed transcriptions only while their entire source text is unchanged.
    previous = {row['id']: row for row in json.loads(path.read_text())} if path.exists() else {}
    for case in cases:
        old = previous.get(case['id'], {})
        if old.get('text') == case['text'] and old.get('resolved_cells') == case.get('resolved_cells'):
            for key in ('item', 'items', 'expected', 'spec', 'specs', 'examples', 'comparisons', 'unresolved_reason'):
                if key in old:
                    case[key] = old[key]
    for case in cases:
        if not any(case.get(key) for key in ('item', 'items', 'spec', 'specs', 'examples')) and (
            examples := base_table_examples(case)
        ):
            case['examples'] = examples
    from pricing.triage.guide_classification import classify

    for case in cases:
        case.update(classify(case))
        if not any(case.get(key) for key in ('item', 'items', 'spec', 'specs', 'examples', 'comparisons')):
            case.setdefault(
                'unresolved_reason',
                'Concrete item and expected outcome not yet transcribed: ' + case['classification_reason'],
            )
    atomic_json(path, cases)
    return cases


def main():
    from pricing.knowledge.refresh import atomic_json
    from pricing.triage.engine import Tables, assess

    cases = build_cases()
    tables = Tables().load()
    report = evaluate(cases, lambda item: assess(item, tables))
    atomic_json(ROOT / 'inventory_tracking/corpus/data/score-guides.json', report)
    print(
        json.dumps(
            {
                'cases': len(cases),
                'classifications': report['classifications'],
                'table_score': report['table_score'],
                'groups': report['groups'],
                'unresolved': len(report['unresolved']),
                'failures': len(report['failures']),
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
