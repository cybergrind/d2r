"""Compact reports for fungible materials with validated native identities."""

from inventory_tracking.appraisal.material_sets import set_lines
from inventory_tracking.appraisal.sections import current_price_lines, review_lines, utility_lines


def commodity_lines(result):
    assessment = result.get('assessment', {})
    contract = assessment.get('contract') or {}
    if contract.get('policy') not in ('socket_material', 'quest_material'):
        return None
    item = result['extraction']['item']
    utility = assessment.get('utility') or {}
    lines = ['Material: ' + utility.get('name', item.get('name', 'Unknown material'))]
    estimate = result.get('price_estimate') or {}
    if 'triage' not in result:
        if estimate.get('unavailable_reason') == 'no_matches':
            lines.append('Unit price: unavailable — no matching scoped commodity quotes.')
        else:
            lines.extend(line.replace('Price:', 'Unit price:', 1) for line in current_price_lines(result))
    for lot in result.get('commodity_bulk', []):
        price = lot['estimate']
        value = price.get('estimate_ist')
        if value is not None:
            quantity = lot['quantity']
            lines.append(f'Bulk {quantity}: ~{value * quantity:g} Ist total (~{value:g} each; asks)')
    owned = result.get('owned') or {}
    basket = result.get('commodity_set')
    if basket and basket['estimate'].get('estimate_ist') is not None:
        price = basket['estimate']
        lines.append(f'Complete {basket["name"]}: ~{price["estimate_ist"]:g} Ist (asks; {basket["quantity_label"]})')
        lines.append('  Set quotes observed: ' + ', '.join(price['dates']))
    lines.extend(set_lines(owned.get('material_set')))
    if type(owned.get('count')) is int and not owned.get('material_set'):
        lines.append(f'Owned quantity: {owned["count"]}')
    lines.extend('Use: ' + line.strip() for line in utility_lines(result)[1:])
    lines.extend('Unreadable: ' + issue for issue in review_lines(result['extraction']))
    return lines
