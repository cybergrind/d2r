"""Separate exact cohorts for each verified armor-upgrade defense outcome."""

from dataclasses import replace

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier
from pricing.knowledge.assessment.mechanics.upgrade_comparisons import upgrade_action


def armor_upgrade_requests(facts, contract, paths):
    if (
        contract is None
        or contract.policy != 'named'
        or contract.family not in ('armor', 'helm', 'shield', 'accessory')
        or facts.rarity not in ('unique', 'set')
        or facts.identified is not True
        or not facts.capture_complete
        or facts.runeword
    ):
        return ()
    requests = []
    for path in paths:
        outcome = path.defense_outcome
        if outcome is None:
            continue
        for defense in outcome['possible_values']:
            destination = replace(
                contract,
                base_code=path.target_code,
                base_tier=base_tier(path.target_code),
                properties={**contract.properties, '1855': defense},
            )
            preparation = {
                **upgrade_action(path, 'upgrade_armor'),
                'defense': defense,
                'defense_min': outcome['min'],
                'defense_max': outcome['max'],
            }
            requests.append(
                ComparisonRequest(
                    f'upgrade_{path.target_code}_defense_{defense}',
                    f'armor_after_upgrade_{path.target_code}_defense_{defense}',
                    destination.to_dict(),
                    state='prepared',
                    preparation=preparation,
                )
            )
    return tuple(requests)
