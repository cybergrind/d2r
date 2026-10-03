"""Separate asking cohorts for normalized rune/gem lots; never inferred turnover."""

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables


def bulk_quotes(contract, rows, *, today):
    if not contract or contract.get('policy') != 'socket_material':
        return []
    rows = list(rows)
    quantities = sorted(
        {
            row['amount']
            for row in rows
            if row.get('unit_policy') == 'stack_total' and type(row.get('amount')) is int and row['amount'] > 1
        }
    )
    result = []
    for quantity in quantities:
        comparisons = evaluate(contract, rows, lot_quantity=quantity)
        if comparisons['accepted']:
            result.append(
                {
                    'quantity': quantity,
                    'unit': 'per_item',
                    'evidence_kind': 'ask',
                    'liquidity': 'unverified',
                    'estimate': price_from_comparables(comparisons, today=today),
                }
            )
    return result
