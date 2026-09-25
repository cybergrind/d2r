"""Exact upgraded-weapon cohorts; rolled armor defense is not projected."""

from collections import Counter
from dataclasses import replace

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier


def upgrade_outcome_requests(facts, contract, paths):
    if (
        contract is None
        or contract.family != 'weapon'
        or contract.policy not in ('named', 'affixed')
        or facts.rarity not in ('unique', 'set', 'rare')
        or facts.identified is not True
        or not facts.capture_complete
        or facts.runeword
    ):
        return ()
    results = []
    for path in paths:
        destination = replace(
            contract,
            name=path.target_name if contract.policy == 'affixed' else contract.name,
            base_code=path.target_code,
            base_tier=base_tier(path.target_code),
        )
        action = upgrade_action(path, 'upgrade_weapon')
        results.append(
            ComparisonRequest(
                f'upgrade_{path.target_code}',
                f'weapon_after_upgrade_{path.target_code}',
                destination.to_dict(),
                state='prepared',
                preparation=action,
            )
        )
    return tuple(results)


def upgrade_action(path, action):
    resources = Counter(name for step in path.steps for name in step['resources'])
    return {
        'action': action,
        'destination': path.target_name,
        'source_code': path.source_code,
        'target_code': path.target_code,
        'feasibility': 'possible',
        'preconditions': list(path.preconditions),
        'resources': [{'name': name, 'quantity': count} for name, count in resources.items()],
        'steps': path.to_dict()['steps'],
    }
