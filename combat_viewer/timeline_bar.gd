extends Control
## Scrub bar for the replay viewer. Shows a tick range (25 ticks a second) with the recorded and
## policy casts and kills in two lanes, the ticks the recorded character was moving, the moments
## worth looking at, the loop range and the cursor. Click or drag to seek; the main script owns
## the keyboard.

signal seek_requested(tick: int)  # the user clicked or dragged to this tick (already clamped to the range)

const Palette := preload("res://palette.gd")
const RATE := 25.0  # ticks a second

const PAD := 6.0  # horizontal padding inside the control
const MOMENT_H := 14.0
const LANE_H := 26.0
const RUN_H := 5.0
const MOMENT_TOP := 0.0
const REC_TOP := MOMENT_H
const POL_TOP := REC_TOP + LANE_H
const RUN_TOP := POL_TOP + LANE_H
const RULER_TOP := RUN_TOP + RUN_H
const CAST_BOTTOM_FRAC := 2.0 / 3.0  # casts sit in the upper two thirds of a lane
const KILL_TOP := 18.0  # kill triangles start in the lower third of a lane
const KILL_HALF_W := 3.5
const KILL_H := 7.0
const MIN_LABEL_GAP := 90.0  # pixels between ruler labels
const STEPS: Array[int] = [1, 2, 5, 10, 15, 30, 60, 120, 300]  # ruler label steps, seconds

var _first: int = 0
var _last: int = 0
var _recorded_casts: PackedInt32Array = PackedInt32Array()
var _policy_casts: PackedInt32Array = PackedInt32Array()
var _recorded_kills: PackedInt32Array = PackedInt32Array()
var _policy_kills: PackedInt32Array = PackedInt32Array()
var _recorded_moves: Array = []  # [t0, t1] pairs of the runs' own moves, when the file has them
var _policy_moves: Array = []
var _running: PackedInt32Array = PackedInt32Array()
var _moments: PackedInt32Array = PackedInt32Array()
var _moment_selected: int = -1
var _loop_first: int = -1
var _loop_last: int = -1
var _tick: int = 0

var _dragging: bool = false
var _emitted: int = 0  # the last tick sent by seek_requested


## Sets up the control's size, input and focus.
func _init() -> void:
	custom_minimum_size = Vector2(0, 110)
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_NONE


## Sets the ticks shown, inclusive. last must be >= first.
func set_range(first: int, last: int) -> void:
	_first = first
	_last = last
	queue_redraw()


## Sets the cast and kill ticks of both runs (each ascending).
func set_marks(recorded_casts: PackedInt32Array, policy_casts: PackedInt32Array,
		recorded_kills: PackedInt32Array, policy_kills: PackedInt32Array) -> void:
	_recorded_casts = recorded_casts
	_policy_casts = policy_casts
	_recorded_kills = recorded_kills
	_policy_kills = policy_kills
	queue_redraw()


## Sets the moves (dictionaries with "t0", "t1") of the two runs; empty arrays draw nothing.
func set_moves(recorded_moves: Array, policy_moves: Array) -> void:
	_recorded_moves = recorded_moves
	_policy_moves = policy_moves
	queue_redraw()


## Sets the ticks the recorded character was moving, as flat [first, last, first, last, ...] pairs.
func set_running(spans: PackedInt32Array) -> void:
	_running = spans
	queue_redraw()


## Sets the moments worth looking at, as flat [first, last, ...] pairs. selected is the 0-based
## index of the highlighted moment, or -1 for none.
func set_moments(spans: PackedInt32Array, selected: int) -> void:
	_moments = spans
	_moment_selected = selected
	queue_redraw()


## Sets the tick range being looped, or (-1, -1) for none.
func set_loop(first: int, last: int) -> void:
	_loop_first = first
	_loop_last = last
	queue_redraw()


## Sets the cursor tick.
func set_tick(tick: int) -> void:
	if tick == _tick:
		return
	_tick = tick
	queue_redraw()


## Maps a tick to an x position inside the control.
func _x_of(tick: float) -> float:
	if _last <= _first:
		return PAD
	var plot_w: float = size.x - 2.0 * PAD
	return PAD + (tick - float(_first)) / float(_last - _first) * plot_w


## Maps an x position inside the control back to a tick, clamped to the range.
func _tick_at(x: float) -> int:
	if _last <= _first:
		return _first
	var plot_w: float = size.x - 2.0 * PAD
	if plot_w <= 0.0:
		return _first
	var t: float = float(_first) + (x - PAD) / plot_w * float(_last - _first)
	return clampi(roundi(t), _first, _last)


## Sends a seek to the given tick.
func _seek(tick: int) -> void:
	_emitted = tick
	seek_requested.emit(tick)


func _gui_input(event: InputEvent) -> void:
	var button: InputEventMouseButton = event as InputEventMouseButton
	if button != null and button.button_index == MOUSE_BUTTON_LEFT:
		if button.pressed:
			_dragging = true
			_seek(_tick_at(button.position.x))
		else:
			_dragging = false
		accept_event()
		return
	var motion: InputEventMouseMotion = event as InputEventMouseMotion
	if motion != null and _dragging:
		var t: int = _tick_at(motion.position.x)
		if t != _emitted:
			_seek(t)
		accept_event()


func _draw() -> void:
	var w: float = size.x
	var h: float = size.y

	# 1. Background.
	draw_rect(Rect2(Vector2.ZERO, size), Palette.PANEL, true)
	draw_rect(Rect2(Vector2(0.5, 0.5), size - Vector2.ONE), Palette.PANEL_EDGE, false, 1.0)

	# 2. Moments band.
	var pairs: int = _moments.size() >> 1
	for k: int in range(pairs):
		var alpha: float = 1.0 if k == _moment_selected else 0.45
		var rect: Rect2 = _span_rect(_moments[2 * k], _moments[2 * k + 1], MOMENT_TOP, MOMENT_H, 3.0)
		draw_rect(rect, Color(Palette.MOMENT, alpha), true)

	# 3 and 4. The two lanes.
	_draw_lane(REC_TOP, _recorded_casts, _recorded_kills, Palette.RECORDED, "recorded")
	_draw_lane(POL_TOP, _policy_casts, _policy_kills, Palette.POLICY, "policy")

	_draw_moves(REC_TOP, _recorded_moves, Palette.RECORDED)
	_draw_moves(POL_TOP, _policy_moves, Palette.POLICY)

	# 5. Running band.
	var run_pairs: int = _running.size() >> 1
	for k: int in range(run_pairs):
		var rect: Rect2 = _span_rect(_running[2 * k], _running[2 * k + 1], RUN_TOP, RUN_H, 1.0)
		draw_rect(rect, Color(Palette.TEXT_DIM, 0.5), true)

	# 6. Time ruler.
	_draw_ruler(w)

	# 7. Loop range, over the lanes.
	if _loop_first >= 0 and _loop_last >= _loop_first:
		var x0: float = _x_of(_loop_first)
		var x1: float = _x_of(_loop_last)
		var loop_rect: Rect2 = Rect2(x0, REC_TOP, maxf(x1 - x0, 2.0), POL_TOP + LANE_H - REC_TOP)
		draw_rect(loop_rect, Palette.MOMENT, false, 2.0)

	# 8. Cursor, last.
	var cursor_x: float = _x_of(clampi(_tick, _first, _last))
	draw_rect(Rect2(cursor_x - 1.0, 0.0, 2.0, h), Palette.CURSOR, true)


## Rectangle for a tick span, at least min_w wide.
func _span_rect(first: int, last: int, y: float, height: float, min_w: float) -> Rect2:
	var x0: float = _x_of(first)
	var x1: float = _x_of(last)
	return Rect2(x0, y, maxf(x1 - x0, min_w), height)


## One run's lane: cast lines in the upper two thirds, kill triangles in the lower third, and its label.
func _draw_lane(top: float, casts: PackedInt32Array, kills: PackedInt32Array, color: Color, label: String) -> void:
	var cast_color: Color = Color(color, 0.7)
	var cast_bottom: float = top + LANE_H * CAST_BOTTOM_FRAC
	for t: int in casts:
		var x: float = roundf(_x_of(t)) + 0.5
		draw_line(Vector2(x, top + 2.0), Vector2(x, cast_bottom), cast_color, 1.0)
	var kill_top: float = top + KILL_TOP
	for t: int in kills:
		var x: float = _x_of(t)
		var points: PackedVector2Array = PackedVector2Array([
			Vector2(x - KILL_HALF_W, kill_top),
			Vector2(x + KILL_HALF_W, kill_top),
			Vector2(x, kill_top + KILL_H),
		])
		draw_colored_polygon(points, color)
	var font: Font = get_theme_default_font()
	var font_size: int = maxi(get_theme_default_font_size() - 5, 8)
	var label_size: Vector2 = font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size)
	draw_rect(Rect2(1.0, top + 1.0, PAD + label_size.x + 4.0, LANE_H - 2.0), Color(Palette.PANEL, 0.85), true)
	draw_string(font, Vector2(PAD, top + LANE_H * 0.5 + font_size * 0.35), label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)


## A run's moves as short bars along the bottom of its lane, from the decision to the arrival.
func _draw_moves(top: float, moves: Array, color: Color) -> void:
	for item: Variant in moves:
		var step: Dictionary = item
		var rect: Rect2 = _span_rect(int(step["t0"]), int(step["t1"]), top + LANE_H - 6.0, 4.0, 3.0)
		draw_rect(rect, Color(color, 0.9), true)


## Tick marks and minute:second labels under the lanes, labelled from the first tick.
func _draw_ruler(w: float) -> void:
	var y0: float = RULER_TOP
	var span_s: float = float(_last - _first) / RATE
	var plot_w: float = w - 2.0 * PAD
	var pixels_per_s: float = plot_w / maxf(span_s, 0.001)
	var step: int = STEPS[STEPS.size() - 1]
	for candidate: int in STEPS:
		if float(candidate) * pixels_per_s >= MIN_LABEL_GAP:
			step = candidate
			break
	var font: Font = get_theme_default_font()
	var font_size: int = maxi(get_theme_default_font_size() - 5, 8)
	var max_sec: int = floori(span_s)
	for sec: int in range(0, max_sec + 1, step):
		var x: float = _x_of(_first + roundi(float(sec) * RATE))
		draw_line(Vector2(x, y0), Vector2(x, y0 + 5.0), Palette.TEXT_DIM, 1.0)
		var minutes: int = floori(float(sec) / 60.0)
		var seconds: int = sec - minutes * 60
		draw_string(font, Vector2(x + 3.0, y0 + 5.0 + font_size), "%d:%02d" % [minutes, seconds],
				HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Palette.TEXT_DIM)
