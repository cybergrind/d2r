"""HUD process plumbing: slot config, guide widgets from display lines, one canvas per scene."""

from inventory_tracking.config import HUD
from inventory_tracking.hud.process import acquire_instance, card_widgets, guide_widgets, terror_widgets
from inventory_tracking.osd.level_map import MapCard
from inventory_tracking.presentation import StyledLine


def test_guide_slot_is_a_game_window_fraction():
    slot = HUD.slots['guide']
    assert 0 <= slot.x < 0.5
    assert 0 <= slot.y < 0.5


def test_display_lines_become_one_guide_widget_and_nothing_when_hidden():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0))
    line = StyledLine('↗  Summoner: north', arrow='↗')

    [widget] = guide_widgets([line, card])

    assert (widget.id, widget.kind, widget.slot) == ('guide', 'guide', 'guide')
    assert widget.payload == {'lines': [line.to_payload()], 'map': card.to_payload()}
    assert guide_widgets([]) == []


def test_only_one_canvas_runs_per_scene_directory(tmp_path):
    first = acquire_instance(tmp_path)
    try:
        assert first is not None
        assert acquire_instance(tmp_path) is None
    finally:
        first.close()
    second = acquire_instance(tmp_path)
    assert second is not None
    second.close()


def test_producers_do_not_load_the_pango_renderer():
    import subprocess
    import sys

    code = 'import sys, inventory_tracking.hud.process; print("gi" in sys.modules)'
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == 'False'


def test_card_lines_become_one_text_widget_in_the_assessment_slot():
    [widget] = card_widgets(['Ring', StyledLine('Price unknown')])

    assert (widget.id, widget.kind, widget.slot) == ('card', 'text', 'assessment')
    assert widget.payload == {'lines': [StyledLine('Ring').to_payload(), StyledLine('Price unknown').to_payload()]}
    assert card_widgets([]) == []


def test_identify_card_has_its_own_widget_id_so_it_stacks_with_the_shop_card():
    [widget] = card_widgets(['Identified 1'], 'identify')

    assert (widget.id, widget.kind, widget.slot) == ('identify', 'text', 'assessment')


def test_assessment_slot_sits_right_of_the_guide_and_is_width_capped():
    guide, card = HUD.slots['guide'], HUD.slots['assessment']
    assert card.x > guide.x + 0.12  # the guide card is ~0.11 of a 2560 px window wide
    assert card.max_width < 0.5


def test_rune_rows_become_a_loot_widget_without_a_map():
    from inventory_tracking.hud.process import loot_widgets

    line = StyledLine('↘  Ber Rune: east', arrow='↘')

    [widget] = loot_widgets([line])

    assert (widget.id, widget.kind, widget.slot) == ('runes', 'guide', 'loot')
    assert widget.payload == {'lines': [line.to_payload()], 'map': None}
    assert loot_widgets([]) == []


def test_loot_slot_sits_below_the_guide_card():
    assert HUD.slots['loot'].x == HUD.slots['guide'].x
    assert HUD.slots['loot'].y > HUD.slots['guide'].y + 0.2  # the guide card is ~0.23 of a 1422 px window tall


def test_rune_marks_default_to_io_and_up():
    from inventory_tracking.config import APPRAISAL
    from inventory_tracking.loot.runes import is_valuable_rune

    assert APPRAISAL.rune_marks is True
    assert APPRAISAL.rune_minimum == 'r16'  # Io and up (user, 2026-09-30); loot/data/runes.json: 640 = r16 Io
    assert is_valuable_rune(640, minimum=APPRAISAL.rune_minimum)  # Io
    assert not is_valuable_rune(639, minimum=APPRAISAL.rune_minimum)  # Hel


def test_terror_card_is_a_text_widget_in_its_own_top_right_slot():
    [widget] = terror_widgets(['Terror · Black Marsh'])

    assert (widget.id, widget.kind, widget.slot) == ('terror', 'text', 'terror')
    assert terror_widgets([]) == []
    slot = HUD.slots['terror']
    assert slot.x > HUD.slots['assessment'].x + HUD.slots['assessment'].max_width  # never under an Alt+D card
    assert slot.y <= 0.03  # at the top of the window (user, 2026-10-04)
