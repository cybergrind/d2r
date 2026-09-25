"""Typed records for the item collection database.

An ItemRecord is built from a decoded observation exactly as Alt+D freezes it; a
Placement says where one copy of that item was seen. Nothing here reads memory or
the knowledge base.
"""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from inventory_tracking.collection.fingerprint import fingerprint


Container = Literal['inventory', 'cube', 'equipped', 'mercenary', 'stash', 'shared_stash', 'materials']
SHARED_OWNER = 'shared'
ContainerKey = tuple[str, str, int | None]  # owner, container, tab


class Record(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')


class Character(Record):
    name: str = Field(min_length=1)
    class_id: int | None = None
    class_name: str | None = None
    level: int | None = None


class Location(Record):
    owner: str = Field(min_length=1)
    container: Container
    tab: int | None = None
    x: int = Field(ge=0)
    y: int = Field(ge=0)

    @property
    def key(self) -> ContainerKey:
        return self.owner, self.container, self.tab

    @property
    def label(self) -> str:
        where = self.container.replace('_', ' ')
        if self.tab is not None:
            where += f' {self.tab}'
        return f'{self.owner} · {where} ({self.x},{self.y})'

    @classmethod
    def from_source(cls, source: dict[str, Any], character: str, *, tab: int | None = None) -> Self:
        """Map an observation's verified container/owner/position onto a collection location."""
        page = source['container']['page']
        owner_type = source.get('owner_type', 0)
        owner = character
        container: Container
        if page == 0:
            container = 'inventory'
        elif page == 3:
            container = 'cube'
        elif page == 255:
            container = 'mercenary' if owner_type == 1 else 'equipped'
        elif page == 4:
            name = source['container']['name']
            if name == 'Shared stash':
                owner, container = SHARED_OWNER, 'shared_stash'
            elif name == 'Materials stash':
                owner, container = SHARED_OWNER, 'materials'
            else:
                container = 'stash'
        else:
            raise ValueError(f'Unsupported container page {page}')
        if container != 'shared_stash' and tab is not None:
            raise ValueError('Only shared stash locations carry a tab')
        x, y = source['position']
        return cls(owner=owner, container=container, tab=tab, x=x, y=y)


class ItemRecord(Record):
    fingerprint: str = Field(min_length=64, max_length=64)
    base_code: str
    base_name: str
    name: str
    rarity: str
    identified: bool | None = None
    ethereal: bool | None = None
    sockets: int | None = None
    socket_contents: str | None = None
    socket_items: list[str] = []
    runeword: str | None = None
    set_name: str | None = None
    stat_lines: list[str] = []
    unresolved: int = 0
    quantity: int | None = None
    width: int | None = None
    height: int | None = None
    observation: dict[str, Any]

    @classmethod
    def from_observation(cls, observation: dict[str, Any]) -> Self:
        item = observation['item']
        lines = [s['text'] for s in observation.get('decoded_stats', []) if s.get('text')]
        return cls(
            fingerprint=fingerprint(observation),
            base_code=item['base_code'],
            base_name=item['base_name'],
            name=item['name'],
            rarity=item['rarity'],
            identified=item.get('identified'),
            ethereal=item.get('ethereal'),
            sockets=item.get('sockets'),
            socket_contents=item.get('socket_contents'),
            socket_items=[s['name'] for s in item.get('socket_items', []) if s.get('name')],
            runeword=item.get('runeword'),
            set_name=item.get('set_name'),
            stat_lines=lines,
            unresolved=len(observation.get('unresolved_stats', [])),
            quantity=item.get('quantity'),
            width=item.get('width'),
            height=item.get('height'),
            observation=observation,
        )

    @property
    def search_text(self) -> str:
        """Lower-cased text every search matches against: names, set, runeword, sockets, stats."""
        parts = [
            self.name,
            self.base_name,
            self.base_code,
            self.rarity,
            self.set_name or '',
            self.runeword or '',
            *self.socket_items,
            *self.stat_lines,
        ]
        if self.ethereal:
            parts.append('ethereal')
        if self.identified is False:
            parts.append('unidentified')
        return '\n'.join(p for p in parts if p).lower()


class ContainerSpace(Record):
    """Free cells of one grid; `rows` are '.'/'#' strings, `fits` greedy counts per WxH."""

    owner: str
    container: Container
    tab: int | None = None
    width: int
    height: int
    free: int
    occupied: int
    rows: list[str]
    fits: dict[str, int]

    @property
    def key(self) -> ContainerKey:
        return self.owner, self.container, self.tab


class Sighting(Record):
    item: ItemRecord
    location: Location


class Placement(Record):
    id: int | None = None
    fingerprint: str
    location: Location
    capture_id: str
    seen_at: str
    gone_at: str | None = None


class CaptureRun(Record):
    id: str = Field(min_length=1)
    character: Character
    containers: list[ContainerKey]
    started_at: str
    status: Literal['running', 'complete', 'failed'] = 'running'
    item_count: int = 0


class CaptureSummary(Record):
    total: int
    new: int
    moved: int
    unchanged: int
    gone: int

    def __str__(self) -> str:
        return f'{self.total} items · {self.new} new · {self.moved} moved · {self.gone} gone'
