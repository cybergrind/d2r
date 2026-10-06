"""Semantic colors shared by terminal and GTK renderers; text is always literal."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from html import escape
from types import MappingProxyType

from rich.style import Style
from rich.text import Text


class Tone(StrEnum):
    DEFAULT = 'default'
    METADATA = 'metadata'
    HEADING = 'heading'
    NORMAL = 'normal'
    INFERIOR = 'inferior'
    SOCKETED = 'socketed'
    MAGIC = 'magic'
    RARE = 'rare'
    UNIQUE = 'unique'
    SET = 'set'
    CRAFTED = 'crafted'
    RUNEWORD = 'runeword'
    PERFECT = 'perfect'
    LOW = 'low'
    WARNING = 'warning'
    VALUABLE = 'valuable'
    DEMAND = 'demand'
    PREFERRED = 'preferred'
    LEVELING = 'leveling'
    TIER_HIGH = 'tier_high'
    TIER_MED = 'tier_med'
    TIER_LOW = 'tier_low'
    TIER_TRASH = 'tier_trash'
    ETHEREAL_TARGET = 'ethereal_target'
    ETHEREAL_DESIRED = 'ethereal_desired'
    ETHEREAL_UNDESIRED = 'ethereal_undesired'
    STAT_DESIRABLE = 'stat_desirable'
    STAT_SUPPORTING = 'stat_supporting'
    # Level guide / loot marks (user, 2026-09-30): one colour per POI kind.
    LEVEL_NEXT = 'level_next'
    LEVEL_PREVIOUS = 'level_previous'
    WAYPOINT = 'waypoint'
    POI = 'poi'
    EXIT = 'exit'
    HERALD = 'herald'  # a live Terror Zone Herald on the level map
    MOB = 'mob'  # a hostile monster alive, level map
    MOB_LEADER = 'mob_leader'  # a unique, champion or super unique alive, level map
    MOB_DANGER = 'mob_danger'  # a monster of a deadly pack (terror/danger.py)
    MOB_CAUTION = 'mob_caution'  # a monster of a pack to be careful with


PALETTE = MappingProxyType(
    {
        Tone.DEFAULT: '#ffffff',
        Tone.METADATA: '#aaaaaa',
        Tone.HEADING: 'bold #dddddd',
        Tone.NORMAL: '#ffffff',
        Tone.INFERIOR: '#aaaaaa',
        Tone.SOCKETED: '#aaaaaa',
        Tone.MAGIC: '#8888ff',
        Tone.RARE: '#ffff77',
        Tone.UNIQUE: '#c7b377',
        Tone.SET: '#55dd55',
        Tone.CRAFTED: '#ffaa55',
        Tone.RUNEWORD: '#c7b377',
        Tone.PERFECT: 'bright_green',
        Tone.LOW: 'bright_red',
        Tone.WARNING: 'bright_yellow',
        Tone.VALUABLE: 'bold bright_magenta',
        Tone.DEMAND: 'bold bright_cyan',
        Tone.PREFERRED: 'bold bright_green',
        Tone.LEVELING: 'bold #66ddbb',
        Tone.TIER_HIGH: 'bold #55ff55',
        Tone.TIER_MED: 'bold #ffff55',
        Tone.TIER_LOW: 'bold #77aaff',
        Tone.TIER_TRASH: 'bold #ff5555',
        Tone.ETHEREAL_TARGET: '#77aaff',
        Tone.ETHEREAL_DESIRED: 'bright_green',
        Tone.ETHEREAL_UNDESIRED: 'bright_red',
        Tone.STAT_DESIRABLE: 'bright_green',
        Tone.STAT_SUPPORTING: '#77aaff',
        Tone.LEVEL_NEXT: '#44e05a',
        Tone.LEVEL_PREVIOUS: '#c080ff',
        Tone.WAYPOINT: '#6fa8ff',
        Tone.POI: '#ffee33',
        Tone.EXIT: '#dddddd',
        Tone.HERALD: '#ff3d6e',
        Tone.MOB: '#a8463e',
        Tone.MOB_LEADER: '#ff4dff',
        Tone.MOB_DANGER: '#ff6a00',
        Tone.MOB_CAUTION: '#ffb14a',
    }
)


@dataclass(frozen=True)
class StyledSpan:
    text: str
    tone: Tone


@dataclass(frozen=True)
class StyledLine:
    text: str
    tone: Tone = Tone.DEFAULT
    osd: bool = True
    spans: tuple[StyledSpan, ...] = ()
    arrow: str | None = None

    def __post_init__(self):
        if self.arrow is not None and self.arrow not in ('→', '↗', '↑', '↖', '←', '↙', '↓', '↘'):
            raise ValueError('Invalid directional arrow')
        object.__setattr__(self, 'spans', tuple(self.spans))
        if self.spans and ''.join(span.text for span in self.spans) != self.text:
            raise ValueError('Styled spans must preserve the complete literal line')

    def to_payload(self) -> dict:
        result = {'text': self.text, 'tone': self.tone.value}
        if self.arrow is not None:
            result['arrow'] = self.arrow
        if self.spans:
            result['spans'] = [{'text': span.text, 'tone': span.tone.value} for span in self.spans]
        return result

    @classmethod
    def from_payload(cls, value) -> StyledLine:
        if not isinstance(value, dict) or not isinstance(value.get('text'), str):
            raise ValueError('Invalid styled line')
        spans = value.get('spans', [])
        if not isinstance(spans, list) or any(
            not isinstance(span, dict) or not isinstance(span.get('text'), str) for span in spans
        ):
            raise ValueError('Invalid styled spans')
        return cls(
            value['text'],
            Tone(value.get('tone', 'default')),
            spans=tuple(StyledSpan(span['text'], Tone(span.get('tone', 'default'))) for span in spans),
            arrow=value.get('arrow'),
        )


def render_rich(lines: Iterable[StyledLine]) -> Text:
    text = Text()
    for line in lines:
        for span in line.spans or (StyledSpan(line.text, line.tone),):
            text.append(span.text, style=PALETTE[span.tone])
        text.append('\n')
    return text


def tone_rgb(tone: Tone) -> tuple[float, float, float]:
    """The tone's foreground as cairo RGB floats (white when the palette entry has no colour)."""
    color = Style.parse(PALETTE[tone]).color
    red, green, blue = color.get_truecolor() if color else (255, 255, 255)
    return red / 255, green / 255, blue / 255


def render_markup(lines: Iterable[StyledLine]) -> str:
    rendered = []
    for line in lines:
        spans = []
        for span in line.spans or (StyledSpan(line.text, line.tone),):
            style = Style.parse(PALETTE[span.tone])
            color = style.color.get_truecolor().hex if style.color else '#ffffff'
            weight = 'bold' if style.bold else 'normal'
            spans.append(f'<span foreground="{color}" weight="{weight}">{escape(span.text)}</span>')
        rendered.append(''.join(spans))
    return '\n'.join(rendered)
