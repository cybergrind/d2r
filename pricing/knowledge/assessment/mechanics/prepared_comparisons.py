"""Contracts for reviewed socket outcomes, never current prices."""

from dataclasses import replace

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest


def socket_outcome_requests(facts, contract, uses):
    if contract is None or not facts.capture_complete or facts.identified is not True:
        return ()
    if facts.socket_contents == 'filled':
        from pricing.knowledge.assessment.mechanics.cleared_comparisons import cleared_item_request

        return cleared_item_request(facts, contract)
    if facts.sockets == 0 and facts.socket_contents == 'empty' and contract.policy in ('named', 'affixed'):
        from pricing.knowledge.assessment.mechanics.quality_sockets import quality_socket_requests

        return quality_socket_requests(facts, contract)
    if (
        contract.policy != 'base'
        or facts.rarity not in ('normal', 'superior')
        or facts.sockets != 0
        or facts.socket_contents != 'empty'
    ):
        return ()
    requests = {}
    for use in uses:
        for action in use.get('preparation', ()):
            target = action['target_sockets']
            if not eligible_outcome(action, facts.rarity):
                continue
            # An empty socket adds no stat contributions. Existing base, quality,
            # ethereal state and rolls are retained; no completed word is priced.
            destination = replace(contract, sockets=target)
            requests.setdefault(
                (action['action'], target),
                ComparisonRequest(
                    f'{action["action"]}_{target}',
                    f'empty_base_after_{action["action"]}_{target}',
                    destination.to_dict(),
                    state='prepared',
                    preparation=action,
                ),
            )
    return tuple(requests.values())


def eligible_outcome(action, rarity):
    outcomes = action.get('outcomes')
    if action.get('steps') or not outcomes:
        return False
    conditions = set(action.get('preconditions', ()))
    if action['action'] == 'larzuk':
        return (
            action['feasibility'] in ('possible', 'conditional')
            and not conditions - {'unused_socket_reward', 'item_level'}
            and any(
                row['maximum'] == action['target_sockets'] and row['success_weight'] == row['denominator']
                for row in outcomes
            )
        )
    if action['action'] == 'cube_socket':
        return (
            rarity == 'normal'
            and action['feasibility'] in ('possible', 'conditional')
            and not conditions - {'item_level', 'horadric_cube', 'ingredients_available'}
            and any(row['success_weight'] > 0 for row in outcomes)
        )
    return False
