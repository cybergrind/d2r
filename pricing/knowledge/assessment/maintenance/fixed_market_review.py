"""Auditable pricing reviews for fixed native single-item families."""

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.names import normalize_name


MARKET = 'pricing/data/appraisal-market.jsonl'


@dataclass(frozen=True)
class FixedMarketReview:
    scope: str
    label: str
    description: str
    artifact: str
    family: str
    limit: str
    inputs: tuple[str, ...]
    definitions: Callable
    handler: Callable

    def template_contract(self, code, native):
        # This is a reviewed definition template, not an observation of player stock.
        facts = normalize(
            {
                'item': {
                    'name': native['name'],
                    'base_name': native['name'],
                    'base_code': code,
                    'rarity': 'normal',
                    'identified': True,
                    'ethereal': False,
                    'sockets': 0,
                    'socket_contents': 'empty',
                    'socket_items': [],
                },
                'source': {'stat_capture_complete': True, 'kind': 'native_definition_template'},
                'decoded_stats': [],
                'unresolved_stats': [],
            }
        )
        contract, gaps = self.handler().contract(facts, self.family)
        if contract is None or gaps:
            raise ValueError(f'{self.label} comparison implementation incomplete for {code}: {gaps}')
        return contract.to_dict()

    def audit(self, observations, as_of):
        grouped = defaultdict(list)
        for row in observations:
            grouped[normalize_name(row.get('name'))].append(row)
        rows = []
        for code, native in sorted(self.definitions().items()):
            contract = self.template_contract(code, native)
            candidates = grouped[normalize_name(native['name'])]
            compared = evaluate(contract, candidates)
            price = price_from_comparables(compared, today=as_of)
            if price.get('unavailable_reason') == 'unclassified':
                raise ValueError(f'{self.label} comparison implementation produced an unclassified price.')
            rows.append(
                {
                    'base_code': code,
                    'name': native['name'],
                    'quality': 'normal',
                    'unit_quantity': 1,
                    'contract': contract,
                    'disposition': 'estimate' if price['estimate_ist'] is not None else 'evidence_unavailable',
                    'price': price,
                    'cached_observations': len(candidates),
                    'accepted_observations': [
                        {key: row.get(key) for key in ('listing_id', 'seller_id', 'source', 'observed_at')}
                        for row in compared['accepted']
                    ],
                    'rejection_counts': dict(
                        sorted(Counter(reason for r in compared['rejected'] for reason in r['reasons']).items())
                    ),
                }
            )
        return rows

    def review_inputs(self, root, observations):
        paths = set(self.inputs)
        names = {normalize_name(row['name']) for row in self.definitions().values()}
        sources = {row.get('source') for row in observations if normalize_name(row.get('name')) in names}
        manifest = json.loads((root / 'pricing/data/appraisal-market-manifest.json').read_text())
        for source in sources:
            if not isinstance(source, str) or not source.startswith('pricing/raw/'):
                raise ValueError(f'{self.label} pricing review requires a preserved local raw source')
            path = (root / source).resolve()
            hashes = {row.get('sha256') for row in manifest['files'] if row.get('path') == source}
            if (
                not path.is_relative_to(root.resolve())
                or not path.is_file()
                or len(hashes) != 1
                or hashlib.sha256(path.read_bytes()).hexdigest() not in hashes
            ):
                raise ValueError(f'Stale {self.label.lower()} pricing review raw source: {source}')
            paths.add(source)
        return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in sorted(paths)}

    def build(self, root, as_of):
        observations = [json.loads(line) for line in (root / MARKET).read_text().splitlines()]
        inputs = self.review_inputs(root, observations)
        return {
            'schema_version': 1,
            'scope': self.scope,
            'as_of': as_of.isoformat(),
            'limits': [
                self.limit,
                'Evidence-unavailable is not worthless; comparison code and actual absence are distinct.',
                'Listing update dates, filesystem times and conversion-ladder dates are not observation dates.',
                'Dated review outcome, not a promise that an estimate remains publishable on a later date.',
            ],
            'inputs': inputs,
            'rows': self.audit(observations, as_of),
        }

    def apply(self, rows, review, root):
        if review is None:
            return
        if review.get('schema_version') != 1 or review.get('scope') != self.scope:
            raise ValueError(f'Unsupported {self.label.lower()} pricing review scope')
        as_of = date.fromisoformat(review['as_of'])
        observations = [json.loads(line) for line in (root / MARKET).read_text().splitlines()]
        expected_inputs = self.review_inputs(root, observations)
        if as_of.isoformat() != review['as_of'] or set(review.get('inputs', {})) != set(expected_inputs):
            raise ValueError(f'Incomplete {self.label.lower()} pricing review provenance')
        for path, digest in review['inputs'].items():
            if not (root / path).is_file() or hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Stale {self.label.lower()} pricing review input: {path}')
        if review.get('rows') != self.audit(observations, as_of):
            raise ValueError(f'{self.label} pricing review is incomplete or differs from current comparison results')
        indexed = {record['base_code']: (i, record) for i, record in enumerate(review['rows'])}
        for row in rows:
            codes = row.get('catalog_ids', [])
            if (
                row['kind'] != 'identity'
                or row.get('category') != 'misc'
                or len(codes) != 1
                or row['dimensions']['discovery']['state'] != 'reviewed'
                or codes[0] not in indexed
            ):
                continue
            index, record = indexed[codes[0]]
            if row['name'] != record['name']:
                continue
            outcome = record['price'].get('unavailable_reason', 'supported dated estimate')
            row['dimensions']['market'] = {
                'state': 'reviewed',
                'disposition': record['disposition'],
                'unit_quantity': 1,
                'reason': (
                    f'Reviewed exact {self.description} comparison: {outcome}; bulk lots and recipe use are separate.'
                ),
                'sources': [{'artifact': self.artifact, 'locator': f'/rows/{index}'}],
            }
