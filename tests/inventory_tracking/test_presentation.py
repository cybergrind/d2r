from xml.etree import ElementTree

import pytest
from rich.console import Console

from inventory_tracking.appraisal.presentation import item_tone
from inventory_tracking.presentation import StyledLine, Tone, render_markup, render_rich


@pytest.mark.parametrize('tone', list(Tone))
def test_terminal_and_osd_use_same_color_and_weight(tone):
    line = StyledLine('Literal <text> & [markup]', tone)
    text = render_rich([line])
    style = text.get_style_at_offset(Console(), 0)
    span = ElementTree.fromstring(render_markup([line]))
    assert span.text == line.text
    assert style.color is not None
    assert span.attrib['foreground'] == style.color.get_truecolor().hex
    assert span.attrib['weight'] == ('bold' if style.bold else 'normal')
    assert StyledLine.from_payload(line.to_payload()) == line


@pytest.mark.parametrize(
    ('item', 'expected'),
    [
        ({'rarity': 'magic'}, Tone.MAGIC),
        ({'rarity': 'rare', 'ethereal': True}, Tone.RARE),
        ({'rarity': 'set'}, Tone.SET),
        ({'rarity': 'crafted'}, Tone.CRAFTED),
        ({'rarity': 'unique', 'sockets': 1}, Tone.UNIQUE),
        ({'rarity': 'superior', 'sockets': 4}, Tone.SOCKETED),
        ({'rarity': 'normal', 'ethereal': True}, Tone.SOCKETED),
        ({'rarity': 'superior'}, Tone.NORMAL),
        ({'rarity': 'normal', 'sockets': 4, 'runeword': 'Spirit'}, Tone.RUNEWORD),
        ({'rarity': 'unknown'}, Tone.DEFAULT),
    ],
)
def test_item_quality_color_precedence(item, expected):
    assert item_tone(item) == expected


@pytest.mark.parametrize('payload', [None, {'text': 12}, {'text': 'ok', 'tone': '<b>red</b>'}])
def test_wire_styles_only_accept_known_semantic_tones(payload):
    with pytest.raises(ValueError, match=r'Invalid styled line|is not a valid Tone'):
        StyledLine.from_payload(payload)
