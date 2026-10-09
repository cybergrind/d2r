"""HUD process plumbing: slot config, guide widgets from display lines, one canvas per scene."""

from inventory_tracking.config import HUD
from inventory_tracking.hud.process import acquire_instance, card_widgets, guide_widgets, terror_widgets
from inventory_tracking.osd.level_map import MapCard, MapPoi
from inventory_tracking.presentation import StyledLine


def test_guide_slot_is_a_game_window_fraction():
    # Bottom left, growing up over the life globe's corner: at the top left its rows covered
    # item tooltips of the stash (user, 2026-10-06).
    slot = HUD.slots['guide']
    assert 0 <= slot.x < 0.1
    assert slot.upward
    assert slot.y > 0.9


def test_display_lines_become_a_guide_widget_and_a_map_widget_and_nothing_when_hidden():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0))
    line = StyledLine('↗  Summoner: north', arrow='↗')

    guide, level_map = guide_widgets([line, card])

    assert (guide.id, guide.kind, guide.slot) == ('guide', 'guide', 'guide')
    assert guide.payload == {'lines': [line.to_payload()], 'map': None}
    assert (level_map.id, level_map.kind, level_map.slot) == ('map', 'guide', 'map')
    assert level_map.payload == {'lines': [], 'map': card.to_payload()}
    assert [widget.id for widget in guide_widgets([line])] == ['guide']
    assert [widget.id for widget in guide_widgets([card])] == ['map']
    assert guide_widgets([]) == []


def test_marked_map_dots_also_become_ground_marks_over_the_whole_game_window():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0), (MapPoi('unique', 'leader', 2.0, 3.0),))

    ground, level_map = guide_widgets([card])

    assert (ground.id, ground.kind, ground.slot) == ('ground', 'ground', 'ground')
    assert ground.payload | {'level': 0} == {
        'player': [4.0, 4.0],
        'marks': [['leader', 2.0, 3.0]],
        'live': None,
        'level': 0,
    }
    assert level_map.id == 'map'
    assert (HUD.slots['ground'].x, HUD.slots['ground'].y) == (0, 0)


def test_map_slot_is_centred_in_the_upper_part_of_the_window():
    # Centred (user, 2026-10-04) and moved down from the top edge (fc798cb, 2026-10-05).
    slot = HUD.slots['map']
    assert (slot.x, slot.centered, slot.upward) == (0.5, True, False)
    assert slot.y < 0.25


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


def test_loot_slot_sits_a_third_of_the_way_in_above_the_guide_card():
    assert HUD.slots['loot'].x == 0.33  # user, 2026-10-07; at the left edge before
    assert HUD.slots['loot'].y < HUD.slots['guide'].y - 0.4  # five guide rows are ~0.23 of the window tall


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
    # Left of the game's own corner text (clock, game, level, difficulty: from about 0.91 of the
    # width in the user's screenshot, 2026-10-06), however wide the card gets.
    assert slot.x + slot.max_width <= 0.9


def test_the_panel_layer_names_the_flag_array_and_is_republished_before_its_lease_ends():
    from inventory_tracking.hud.process import PanelBeacon
    from inventory_tracking.hud.scene import LEASE_SECONDS
    from inventory_tracking.native.layout import UI_PANELS_RVA

    class Source:
        pid, images = 7, {'candidate_base': 0x140000000}

    published = []
    beacon = PanelBeacon(Source, published.append)

    beacon.poll(10.0)
    beacon.poll(10.1)
    assert [(w.kind, w.slot, w.payload) for w in published[0]] == [
        ('panels', 'panels', {'live': [7, 0x140000000 + UI_PANELS_RVA]})
    ]
    assert len(published) == 1
    Source.pid = 8  # the game was restarted
    beacon.poll(10.0 + LEASE_SECONDS / 2)
    assert len(published) == 2
    assert published[1][0].payload['live'][0] == 8


def test_the_assessment_slot_is_never_dimmed():
    assert 'assessment' not in HUD.dim_slots
    assert {'guide', 'map', 'ground', 'terror', 'loot'} <= set(HUD.dim_slots)
    assert {'inventory', 'mercenary'} <= set(HUD.dim_panels)
