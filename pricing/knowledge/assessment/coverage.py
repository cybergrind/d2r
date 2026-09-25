"""Publish explicit strategy and reviewed-profile coverage from runtime policies."""

import json
from collections import Counter
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.coverage import ROOT, audit_named
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.assessment.profiles import load_profiles
from pricing.knowledge.assessment.registry import FAMILIES
from pricing.knowledge.definition_store import catalog


def coverage():
    profiles, gaps = load_profiles()
    named = audit_named(catalog().named, _policies(read_artifact(RULES)), {}, ROOT)
    tier_counts = named['counts']
    types = {t for family in FAMILIES for t in family.types}
    bases = list(metadata()['bases'].values())
    return {
        'schema_version': 2,
        'rules_version': 'assessment-1',
        'families': {
            f.name: {'types': sorted(f.types), 'base_count': sum(b['type'] in f.types for b in bases)} for f in FAMILIES
        },
        'unclassified_types': dict(Counter(b['type'] for b in bases if b['type'] not in types)),
        'reviewed_profiles': [
            {k: p[k] for k in ('id', 'build', 'variant', 'side', 'review_status', 'source')} for p in profiles
        ],
        'profile_count': len(profiles),
        'named_tiers': {
            'identities': tier_counts['identities'],
            'reviewed_policies': tier_counts['reviewed_policies'],
            'pending': tier_counts['identities'] - tier_counts['reviewed_policies'],
            'invalid_sources': tier_counts['invalid_sources'],
            'complete': named['identity_policy_complete'],
        },
        'profile_gaps': gaps,
        'price_policies': {
            'base': {
                'coverage': 'partial',
                'implemented': 'Exact empty base variants, armor defense and socket/ethereal facets.',
            },
            'affixed': {
                'coverage': 'partial',
                'implemented': 'Exact magic/rare/crafted modifier sets across equipment, jewelry, charms and jewels.',
            },
            'named': {
                'coverage': 'partial',
                'implemented': 'Verified identity/base, rolls, fixed bonuses and random skill choices.',
            },
            'runeword': {
                'coverage': 'partial',
                'implemented': 'Exact recipe/base, variable rolls and verified fixed recipe/rune/base contributions.',
            },
        },
        'price_policy_gaps': [
            'Remaining unsupported upgrade and named/affixed socket-contribution variants',
            'Remaining native property and character-level formula market projections',
            'Reviewed role-specific secondary-roll bands and cross-base substitutes',
            'Sufficient dated, scoped, independent comparable sellers for every variant',
            'Complete unique/set tier and build-variant coverage',
        ],
        'coverage_claim': 'Family dispatch is not appraisal or price completeness.',
    }


def main():
    result = coverage()
    path = Path(__file__).resolve().parents[2] / 'data/appraisal-assessment-coverage.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('families', 'reviewed_profiles')}))


if __name__ == '__main__':
    main()
