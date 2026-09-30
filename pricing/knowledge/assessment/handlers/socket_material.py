"""Compare one loose rune or gem only with the same native material and grade."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.socket_materials import definitions


class SocketMaterialHandler:
    def contract(self, facts, family):
        gaps = [*facts.gaps, *facts.projection_gaps]
        native = definitions().get(facts.base_code)
        if native is None or (facts.base_name, facts.name, facts.item_type) != (
            native['name'],
            native['name'],
            native['type'],
        ):
            gaps.append('Loose rune/gem identity conflicts with its native definition.')
        for field, expected in (
            ('rarity', 'normal'),
            ('ethereal', False),
            ('sockets', 0),
            ('socket_contents', 'empty'),
        ):
            if getattr(facts, field) != expected:
                gaps.append(f'Loose rune/gem requires {field}={expected!r}.')
        if facts.runeword or facts.stats or facts.properties or facts.socket_items:
            gaps.append(
                'Loose rune/gem has unexpected modifiers or contents; equipment socket effects do not belong here.'
            )
        if gaps:
            return None, list(dict.fromkeys(gaps))
        return ComparableContract(
            1, 'socket_material', family, facts.base_name, 'normal', False, 0, 'empty', {}, base_code=facts.base_code
        ), []
