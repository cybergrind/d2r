"""Enumerate named tier implementation gaps against definitions and cached research.

Identity policy coverage is not complete variant or numeric-price coverage.
Run offline: python -m pricing.knowledge.assessment.maintenance.coverage
"""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from pricing.knowledge.assessment.maintenance.named_evidence import index_evidence
from pricing.knowledge.assessment.maintenance.review_queue import review_queue
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.assessment.policies.sources import source_error, source_identity


ROOT = Path(__file__).resolve().parents[4]


def definition_variants(records):
    rows = []
    for record in records:
        flag = record.get('game_definition', {}).get('spawnable')
        status = {0: 'disabled', 1: 'enabled'}.get(flag, 'unverified') if type(flag) is int else 'unverified'
        rows.append(
            {
                'table_id': record.get('table_id'),
                'base_codes': list(record.get('base_codes', ())),
                'spawnability': status,
            }
        )
    return sorted(rows, key=lambda row: (str(row['table_id']), row['base_codes']))


def audit_named(
    definitions,
    policies,
    research,
    root,
    *,
    variants=None,
    demand=(),
    recommendations=(),
    item_facts=(),
    market_readiness=None,
):
    root = Path(root).resolve()
    if set(policies) - set(definitions):
        raise ValueError('Unknown policy identities')
    indexed = {source_identity(k, r): k for k, r in research.items() if isinstance(r, dict) and r.get('name')}
    evidence = index_evidence(definitions, demand, recommendations, item_facts)
    market = {(row['quality'], row['name']): row for row in market_readiness['items']} if market_readiness else {}
    rows = []
    for identity, definition in sorted(definitions.items()):
        quality, name = identity
        records = definition_variants((variants or {}).get(identity, [definition]))
        states = {record['spawnability'] for record in records}
        spawnability = 'enabled' if 'enabled' in states else 'disabled' if states == {'disabled'} else 'unverified'
        policy = policies.get(identity)
        error = source_error(policy['source'], identity, root) if policy else None
        status = (
            ('invalid_source' if error else 'reviewed_policy')
            if policy
            else ('research_only' if identity in indexed else 'missing_research')
        )
        rows.append(
            {
                'quality': quality,
                'name': name,
                'base_codes': definition['base_codes'],
                'spawnability': spawnability,
                'definition_variants': records,
                'status': status,
                'tier': policy['default_tier'] if policy and not error else None,
                'research_locator': '/' + indexed[identity] if identity in indexed else None,
                'source_error': error,
                'evidence': evidence[identity],
                'market': (
                    market.get(
                        identity, {'scoped_observations': 0, 'structurally_ready': 0, 'gaps': {}, 'examples': {}}
                    )
                    if market_readiness is not None
                    else None
                ),
                'variant_coverage': 'conditional policy; not all variants' if policy else 'unreviewed',
            }
        )
    counts = Counter(row['status'] for row in rows)
    definition_counts = Counter(v['spawnability'] for row in rows for v in row['definition_variants'])
    return {
        'schema_version': 3,
        'market_as_of': market_readiness['as_of'] if market_readiness is not None else None,
        'review_queue': review_queue(rows),
        'definition_counts': {
            'total': sum(definition_counts.values()),
            **{k: definition_counts[k] for k in ('enabled', 'disabled', 'unverified')},
        },
        'spawnability_note': (
            'Drop-generation flags only; disabled or absent flags do not establish trade worth '
            'or remove review obligations.'
        ),
        'research_scope': 'Supplied market research only; missing_research does not mean absent from the full KB.',
        'identity_policy_complete': bool(rows) and counts['reviewed_policy'] == len(rows),
        'evidence_counts': {
            'unreviewed_with_build_or_leveling_evidence': sum(
                row['status'] != 'reviewed_policy'
                and bool(
                    row['evidence']['recommended_build_occurrences'] or row['evidence']['leveling_recommendations']
                )
                for row in rows
            ),
        },
        'counts': {
            'identities': len(rows),
            'reviewed_policies': counts['reviewed_policy'],
            'research_only': counts['research_only'],
            'missing_research': counts['missing_research'],
            'invalid_sources': counts['invalid_source'],
        },
        'rows': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    from pricing.knowledge.assessment.maintenance.market_readiness import audit

    with (ROOT / 'pricing/data/appraisal-market.jsonl').open() as stream:
        market = audit((json.loads(line) for line in stream), today=args.as_of)
    research = json.loads((ROOT / 'pricing/data/wp-i-uniques-misc.json').read_text())
    from pricing.knowledge.definition_store import catalog

    definitions = catalog()
    result = audit_named(
        definitions.named,
        _policies(RULES.read_bytes()),
        research,
        ROOT,
        variants=definitions.named_variants,
        market_readiness=market,
        demand=json.loads((ROOT / 'pricing/data/appraisal-demand.json').read_text())['rows'],
        recommendations=json.loads((ROOT / 'pricing/data/appraisal-recommendations.json').read_text())['rows'],
        item_facts=json.loads((ROOT / 'pricing/data/appraisal-item-facts.json').read_text())['rows'],
    )
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
