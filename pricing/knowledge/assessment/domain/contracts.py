"""Current exact market comparison contract."""

from dataclasses import dataclass, field, fields

from pricing.knowledge.assessment.domain.facts import freeze, thaw


@dataclass(frozen=True)
class ComparableContract:
    version: int
    policy: str
    family: str
    name: str
    rarity: str
    ethereal: bool
    sockets: int
    socket_contents: str
    properties: dict
    # No cross-base substitution, roll tolerance or extra premium affixes in v1.
    mode: str = 'exact_variant'
    base_code: str | None = None
    intrinsic_properties: dict = field(default_factory=dict)
    base_tier: str | None = None
    base_rarity: str | None = None
    socket_payload: tuple[str, ...] = ()
    required_level: int | None = None

    def __post_init__(self):
        object.__setattr__(self, 'properties', freeze(self.properties))
        object.__setattr__(self, 'intrinsic_properties', freeze(self.intrinsic_properties))
        object.__setattr__(self, 'socket_payload', tuple(self.socket_payload))

    def to_dict(self):
        return {f.name: thaw(getattr(self, f.name)) for f in fields(self)}
