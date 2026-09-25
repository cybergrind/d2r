"""After-action ask references with action costs and socket probabilities."""

from collections import Counter


def prepared_price_lines(result):
    lines = []
    for row in result.get('assessment', {}).get('comparison_results', []):
        estimate = row.get('outcome_ask_estimate', {})
        if row.get('state') != 'prepared' or estimate.get('estimate_ist') is None:
            continue
        action = row.get('preparation', {})
        sockets = row['contract']['sockets']
        if action.get('action') == 'larzuk':
            conditional = action['feasibility'] == 'conditional'
            label = (
                f'If Larzuk gives {sockets} empty sockets' if conditional else f'After Larzuk: {sockets} empty sockets'
            )
            details = ['  Requires a socket quest reward; value applies after socketing.']
            if conditional:
                counts = ', '.join(str(c['maximum']) for c in action['outcomes'])
                details.extend(
                    [
                        f'  Possible counts: {counts}.',
                        '  Item level is unknown; confirm the socket cap before spending the reward.',
                    ]
                )
        elif action.get('action') == 'larzuk_magic':
            label = f'If Larzuk gives {sockets} empty sockets'
            chances = '; '.join(
                f'{100 * c["success_weight"] / c["denominator"]:.3g}% at a {c["maximum"]}-socket quest cap'
                for c in action['outcomes']
            )
            details = [f'  Chance: {chances}.', '  Consumes: Larzuk socket reward.']
            if 'item_level' in action['preconditions']:
                details.append('  Item level is unknown; the socket cap is not confirmed.')
        elif action.get('action') == 'cube_socket':
            label = f'If cube gives {sockets} empty sockets'
            chances = '; '.join(
                f'{100 * chance["success_weight"] / chance["denominator"]:.3g}% at a {chance["maximum"]}-socket cap'
                for chance in action['outcomes']
            )
            costs = resource_names(action['resources'])
            details = [f'  Chance: {chances}.', f'  Consumes: {costs}.']
            if 'item_level' in action['preconditions']:
                details.append('  Item level is unknown; the socket cap is not confirmed.')
        elif action.get('action') == 'upgrade_armor':
            label = f'If upgrading to {action["destination"]} rolls {action["defense"]} defense'
            details = [
                f'  Possible defense: {action["defense_min"]}-{action["defense_max"]}; '
                'this quote applies to that roll only.',
                '  Consumes: ' + resource_names(action['resources']) + '.',
                '  Check the new strength, dexterity and level requirements before upgrading.',
            ]
        elif action.get('action') == 'upgrade_weapon':
            label = f'After upgrading to {action["destination"]}'
            details = [
                '  Consumes: ' + resource_names(action['resources']) + '.',
                '  Check the new strength, dexterity and level requirements before upgrading.',
            ]
        elif action.get('action') == 'clear_sockets':
            label = f'After clearing: {sockets} empty sockets'
            destroyed = Counter(action['destroyed_items'])
            details = [
                '  Consumes: ' + resource_names(action['resources']) + '.',
                '  Destroys: '
                + resource_names([{'name': name, 'quantity': count} for name, count in destroyed.items()])
                + '.',
            ]
        else:
            continue
        lines.append(
            f'{label} — {estimate["low_ist"]:g}-{estimate["high_ist"]:g} Ist asking range '
            f'(SC/NL/PC/RotW; {estimate["sellers"]} sellers).'
        )
        lines.extend(details)
        lines.append('  Observed: ' + ', '.join(estimate['dates']))
    return lines


def resource_names(resources):
    return ', '.join(
        (f'{r["quantity"]} x ' if r['quantity'] != 1 else '') + r['name'].removesuffix(' Rune') for r in resources
    )
