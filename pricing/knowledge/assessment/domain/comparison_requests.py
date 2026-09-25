"""Immutable requests keep current-item comparisons separate from preparation."""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.facts import freeze, thaw


@dataclass(frozen=True)
class ComparisonRequest:
    request_id: str
    segment_id: str
    contract: Mapping
    role_ids: tuple[str, ...] = ()
    state: str = 'observed'
    policy_version: int = 1
    preparation: Mapping | None = None

    def __post_init__(self):
        if any(type(v) is not str or not v for v in (self.request_id, self.segment_id)):
            raise ValueError('Comparison request and segment IDs must be nonempty strings')
        if (
            self.state not in ('observed', 'prepared')
            or type(self.policy_version) is not int
            or self.policy_version != 1
        ):
            raise ValueError('Unsupported comparison request state or policy version')
        if not isinstance(self.contract, Mapping) or not self.contract.get('name'):
            raise ValueError('Comparison request requires a named contract')
        if isinstance(self.role_ids, str) or any(type(v) is not str or not v for v in self.role_ids):
            raise ValueError('Comparison role IDs must be nonempty strings')
        if self.preparation is not None:
            if self.state != 'prepared' or self.preparation.get('action') not in (
                'larzuk',
                'larzuk_magic',
                'cube_socket',
                'clear_sockets',
                'upgrade_weapon',
                'upgrade_armor',
            ):
                raise ValueError('Only reviewed preparation outcome comparisons are supported')
            object.__setattr__(self, 'preparation', freeze(self.preparation))
        object.__setattr__(self, 'contract', freeze(self.contract))
        object.__setattr__(self, 'role_ids', tuple(dict.fromkeys(self.role_ids)))

    def to_dict(self):
        return {
            f.name: thaw(getattr(self, f.name))
            for f in fields(self)
            if f.name != 'preparation' or self.preparation is not None
        }
