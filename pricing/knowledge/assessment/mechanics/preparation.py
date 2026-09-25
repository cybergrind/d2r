"""Reviewed socket actions and their existing report wording from one evaluation."""

from pricing.knowledge.assessment.domain.facts import FactStatus
from pricing.knowledge.assessment.domain.preparation import PreparationOption, SocketPreparation
from pricing.knowledge.assessment.mechanics.preparation_costs import with_costs
from pricing.knowledge.utility import cube_outcomes


def prepare_sockets(facts, recipe):
    wanted = recipe['sockets']
    destination = recipe['details']['runeword']
    actions = []

    def result(status, messages):
        return SocketPreparation(status, tuple(messages), tuple(with_costs(action, facts) for action in actions))

    if facts.socket_state.total.status == FactStatus.CONFLICTING:
        return result('unverified', ['Resolve conflicting socket count and contents before preparation.'])
    if facts.sockets is None:
        return result('unverified', ['Read the socket count before choosing this recipe.'])
    if facts.sockets == 0:
        caps = recipe['details'].get('socket_options', {}).get('maximum_by_ilvl_bracket', ())
        if len(caps) not in (1, 3) or any(type(cap) is not int or not 1 <= cap <= 6 for cap in caps):
            return result('unverified', ['Verify base/item-type socket limits before preparing sockets.'])
    if facts.rarity in ('low_quality', 'low quality'):
        from pricing.knowledge.assessment.mechanics.low_quality import prepare_normalized_sockets

        return prepare_normalized_sockets(facts, recipe)
    if facts.sockets not in (0, wanted):
        return result(
            'wrong socket count', [f'Needs exactly {wanted} sockets; existing socket count cannot be changed.']
        )
    if facts.sockets == 0:
        caps = list(recipe['details']['socket_options']['maximum_by_ilvl_bracket'])
        if facts.item_level is not None and len(caps) == 3:
            caps = [caps[0 if facts.item_level <= 25 else 1 if facts.item_level <= 40 else 2]]
        options = sorted(set(caps))
        if options == [wanted]:
            needs = [f'Larzuk gives the required {wanted} sockets.']
        elif wanted in options:
            needs = [f'Needs {wanted} sockets; Larzuk gives {options}, depending on item level.']
        else:
            needs = [f'Needs {wanted} sockets; Larzuk cannot give that count on this base.']
        if facts.rarity in ('normal', 'superior'):
            actions.append(
                PreparationOption(
                    destination,
                    wanted,
                    'larzuk',
                    'possible' if options == [wanted] else 'conditional' if wanted in options else 'impossible',
                    () if len(options) == 1 else ('item_level',),
                    tuple({'maximum': cap, 'success_weight': int(cap == wanted), 'denominator': 1} for cap in options),
                )
            )
        if facts.rarity == 'superior':
            needs.append('Superior bases cannot use the cube socket recipe.')
        elif facts.rarity == 'normal':
            needs.append(
                'Cube socketing is random; its maximum also depends on item level.'
                if facts.item_level is None
                else f'Cube socketing is random; item level {facts.item_level} gives a {options[0]}-socket cap.'
            )
            outcomes = cube_outcomes(caps)
            actions.append(
                PreparationOption(
                    destination,
                    wanted,
                    'cube_socket',
                    'conditional' if any(row['weights'].get(wanted, 0) for row in outcomes) else 'impossible',
                    ('item_level',) if len(outcomes) > 1 else (),
                    tuple(
                        {
                            'maximum': row['maximum'],
                            'success_weight': row['weights'].get(wanted, 0),
                            'denominator': row['denominator'],
                        }
                        for row in outcomes
                    ),
                )
            )
            chances = [
                f'{100 * row["weights"].get(wanted, 0) / row["denominator"]:.3g}% at a {row["maximum"]}-socket cap'
                for row in outcomes
            ]
            if chances:
                needs.append(f'Cube chance for {wanted} sockets: ' + '; '.join(chances) + '.')
        else:
            needs.append('Low-quality bases need a separate repair/socketing assessment.')
        if actions and all(action.feasibility == 'impossible' for action in actions):
            return result('cannot prepare this base', needs)
        return result('needs sockets', needs)
    if facts.socket_contents == 'filled':
        if facts.rarity in ('normal', 'superior'):
            actions.append(PreparationOption(destination, wanted, 'clear_sockets', 'possible', destroys_contents=True))
        return result('needs empty sockets', ['Clearing the sockets destroys the inserted runes/gems/jewels.'])
    if facts.socket_contents != 'empty':
        return result('unverified', ['Read socket contents; all sockets must be empty.'])
    return result('ready', [])
