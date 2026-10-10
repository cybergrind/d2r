extends PanelContainer
## The right-hand panel of the replay viewer. Shows which take this is, the two runs' final scores,
## the running totals at the current playback moment with their difference, the moments worth
## looking at (clickable), and the keys. Recorded casts are always orange (Palette.RECORDED), the
## policy's casts always blue (Palette.POLICY). Every label is built once in _ready; the setters only
## assign text and colour, so they are cheap enough for every playback tick. Call them once the panel
## is in the tree.

signal moment_chosen(index: int)  # the user clicked a moment; index into the array given to set_moments
signal loop_toggled(on: bool)  # the "Loop the moment" check box changed

const Palette := preload("res://palette.gd")

const TICKS_PER_SECOND := 25.0
const RECORDED_LABEL_FALLBACK := "the player's recorded casts"
const POLICY_NAME_FALLBACK := "policy"
const WHOLE_ROWS := [
	["placement_per_combat_second", "life per combat second"],
	["placement_points", "life taken by blades"],
	["kills", "kills"],
	["casts", "casts"],
	["contacts", "monsters touched"],
	["blades_walled", "blades stopped by walls"],
]
const NOW_ROWS := [
	["taken", "life taken"],
	["kills", "kills"],
	["casts", "casts"],
]
const KEYS_TEXT := "Space play/pause · ←/→ step a tick (Shift: a second) · [ / ] speed · Tab next policy · N / P next/previous moment · L loop · V side by side/overlay · F follow the character · wheel zoom · drag pan · Home fit · Esc take list"

var _title: Label
var _subtitle: Label
var _recorded_legend: Label
var _policy_legend: Label
var _policy_headers: Array[Label] = []  # the policy's name, wherever a grid shows the policy column
var _whole_cells: Dictionary = {}  # row key -> {"recorded": Label, "policy": Label}
var _gain_label: Label
var _now_heading: Label
var _now_cells: Dictionary = {}  # row key -> {"recorded": Label, "policy": Label, "difference": Label}
var _moments_heading: Label
var _loop_check: CheckBox
var _list: ItemList
var _moments: Array = []


func _ready() -> void:
	custom_minimum_size = Vector2(520, 0)
	var box := StyleBoxFlat.new()
	box.bg_color = Palette.PANEL
	box.set_content_margin_all(14)
	add_theme_stylebox_override("panel", box)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 8)
	add_child(column)

	_title = _make_label("", Palette.TEXT)
	_title.add_theme_font_size_override("font_size", 24)
	column.add_child(_title)

	_subtitle = _make_label("", Palette.TEXT_DIM)
	_subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(_subtitle)

	column.add_child(_build_legend())
	column.add_child(_build_whole_take())
	column.add_child(_build_now())
	column.add_child(_build_moments())

	var keys := _make_label(KEYS_TEXT, Palette.TEXT_DIM)
	keys.add_theme_font_size_override("font_size", 16)
	keys.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(keys)


## Which take this is.
func set_take(title: String, subtitle: String) -> void:
	_title.text = title
	_subtitle.text = subtitle


## The two runs' final scores (each dictionary has "name", "label" and "score"; a recorded gain is null).
func set_runs(recorded: Dictionary, policy: Dictionary) -> void:
	_recorded_legend.text = str(recorded.get("label", RECORDED_LABEL_FALLBACK))
	_policy_legend.text = str(policy.get("label", POLICY_NAME_FALLBACK))
	var policy_name: String = str(policy.get("name", POLICY_NAME_FALLBACK))
	for header: Label in _policy_headers:
		header.text = policy_name

	var gain_value: Variant = _score(policy).get("gain", null)
	if gain_value is float or gain_value is int:
		var pct: float = snappedf(float(gain_value) * 100.0, 0.1)
		var sign_text := "+" if pct > 0.0 else ("-" if pct < 0.0 else "")
		_gain_label.text = "policy gain %s%.1f%%" % [sign_text, absf(pct)]
		var gain_color: Color = Palette.TEXT_DIM
		if pct > 0.0:
			gain_color = Palette.GOOD
		elif pct < 0.0:
			gain_color = Palette.BAD
		_gain_label.add_theme_color_override("font_color", gain_color)
	else:
		_gain_label.text = "policy gain –"
		_gain_label.add_theme_color_override("font_color", Palette.TEXT_DIM)

	var recorded_score := _score(recorded)
	var policy_score := _score(policy)
	for row: Array in WHOLE_ROWS:
		var key: String = str(row[0])
		var cells: Dictionary = _whole_cells[key]
		var recorded_label: Label = cells["recorded"]
		var policy_label: Label = cells["policy"]
		recorded_label.text = _grouped(_num(recorded_score, key))
		policy_label.text = _grouped(_num(policy_score, key))


## The running totals at a playback moment. seconds is the time since the take's start.
func set_totals(seconds: float, recorded: Dictionary, policy: Dictionary) -> void:
	_now_heading.text = "Now, at %s" % _mss(seconds)
	for row: Array in NOW_ROWS:
		var key: String = str(row[0])
		var cells: Dictionary = _now_cells[key]
		var recorded_label: Label = cells["recorded"]
		var policy_label: Label = cells["policy"]
		var difference_label: Label = cells["difference"]
		var recorded_value: int = roundi(_num(recorded, key))
		var policy_value: int = roundi(_num(policy, key))
		var difference: int = policy_value - recorded_value
		recorded_label.text = _grouped(float(recorded_value))
		policy_label.text = _grouped(float(policy_value))
		difference_label.text = _signed(difference)

		var difference_color: Color = Palette.TEXT_DIM
		if key != "casts":  # more casts is neither good nor bad
			if difference > 0:
				difference_color = Palette.GOOD
			elif difference < 0:
				difference_color = Palette.BAD
		difference_label.add_theme_color_override("font_color", difference_color)


## The moments worth looking at, sorted by "first" (ticks since the take's start).
func set_moments(moments: Array) -> void:
	_moments = moments.duplicate()
	_list.clear()
	_moments_heading.text = "Moments worth looking at (%d)" % _moments.size()
	if _moments.is_empty():
		var placeholder := _list.add_item("none found for this policy")
		_list.set_item_selectable(placeholder, false)
		_list.set_item_custom_fg_color(placeholder, Palette.TEXT_DIM)
		return
	for i: int in range(_moments.size()):
		var moment := _as_dict(_moments[i])
		var seconds: float = _num(moment, "first") / TICKS_PER_SECOND
		var text := "%s  %s" % [_mss(seconds), str(moment.get("label", ""))]
		var index := _list.add_item(text)
		_list.set_item_custom_fg_color(index, _kind_color(str(moment.get("kind", ""))))


## Highlight and scroll to a moment without emitting moment_chosen. -1 clears the selection.
func select_moment(index: int) -> void:
	if index < 0 or index >= _moments.size():
		_list.deselect_all()
		return
	_list.select(index)
	_list.ensure_current_is_visible()


## Set the "Loop the moment" check box without emitting loop_toggled.
func set_loop(on: bool) -> void:
	_loop_check.set_pressed_no_signal(on)


func _build_legend() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)
	_recorded_legend = _make_label(RECORDED_LABEL_FALLBACK, Palette.TEXT)
	box.add_child(_legend_row(Palette.RECORDED, _recorded_legend))
	_policy_legend = _make_label(POLICY_NAME_FALLBACK, Palette.TEXT)
	box.add_child(_legend_row(Palette.POLICY, _policy_legend))
	return box


func _legend_row(color: Color, text_label: Label) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var swatch := ColorRect.new()
	swatch.color = color
	swatch.custom_minimum_size = Vector2(18, 18)
	swatch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(swatch)
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(text_label)
	return row


func _build_whole_take() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)
	box.add_child(_make_heading("Whole take"))

	var grid := _make_grid(3)
	box.add_child(grid)
	grid.add_child(_make_label("", Palette.TEXT_DIM))
	grid.add_child(_make_value("recorded", Palette.RECORDED))
	var policy_header := _make_value(POLICY_NAME_FALLBACK, Palette.POLICY)
	_policy_headers.append(policy_header)
	grid.add_child(policy_header)

	for row: Array in WHOLE_ROWS:
		var key: String = str(row[0])
		grid.add_child(_make_label(str(row[1]), Palette.TEXT))
		var recorded_cell := _make_value("", Palette.RECORDED)
		var policy_cell := _make_value("", Palette.POLICY)
		grid.add_child(recorded_cell)
		grid.add_child(policy_cell)
		_whole_cells[key] = {"recorded": recorded_cell, "policy": policy_cell}

	_gain_label = _make_label("", Palette.TEXT_DIM)
	box.add_child(_gain_label)
	return box


func _build_now() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)
	_now_heading = _make_heading("Now, at 0:00")
	box.add_child(_now_heading)

	var grid := _make_grid(4)
	box.add_child(grid)
	grid.add_child(_make_label("", Palette.TEXT_DIM))
	grid.add_child(_make_value("recorded", Palette.RECORDED))
	var policy_header := _make_value(POLICY_NAME_FALLBACK, Palette.POLICY)
	_policy_headers.append(policy_header)
	grid.add_child(policy_header)
	grid.add_child(_make_value("difference", Palette.TEXT_DIM))

	for row: Array in NOW_ROWS:
		var key: String = str(row[0])
		grid.add_child(_make_label(str(row[1]), Palette.TEXT))
		var recorded_cell := _make_value("", Palette.RECORDED)
		var policy_cell := _make_value("", Palette.POLICY)
		var difference_cell := _make_value("", Palette.TEXT_DIM)
		grid.add_child(recorded_cell)
		grid.add_child(policy_cell)
		grid.add_child(difference_cell)
		_now_cells[key] = {"recorded": recorded_cell, "policy": policy_cell, "difference": difference_cell}
	return box


func _build_moments() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_moments_heading = _make_heading("Moments worth looking at (0)")
	box.add_child(_moments_heading)

	_loop_check = CheckBox.new()
	_loop_check.text = "Loop the moment"
	_loop_check.focus_mode = Control.FOCUS_NONE
	_loop_check.toggled.connect(_on_loop_toggled)
	box.add_child(_loop_check)

	_list = ItemList.new()
	_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.custom_minimum_size = Vector2(0, 240)
	_list.auto_height = false
	_list.allow_reselect = true
	_list.focus_mode = Control.FOCUS_NONE
	_list.item_selected.connect(_on_item_selected)
	box.add_child(_list)
	return box


func _on_loop_toggled(on: bool) -> void:
	loop_toggled.emit(on)


func _on_item_selected(index: int) -> void:
	if index >= 0 and index < _moments.size():
		moment_chosen.emit(index)


func _kind_color(kind: String) -> Color:
	match kind:
		"policy_ahead", "idle":
			return Palette.GOOD
		"recorded_ahead":
			return Palette.BAD
		"miss":
			return Palette.MOMENT
		"kill":
			return Palette.ELITE
	return Palette.TEXT


func _make_grid(columns: int) -> GridContainer:
	var grid := GridContainer.new()
	grid.columns = columns
	grid.add_theme_constant_override("h_separation", 18)
	grid.add_theme_constant_override("v_separation", 4)
	return grid


func _make_label(text: String, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_color_override("font_color", color)
	return label


func _make_heading(text: String) -> Label:
	var heading := _make_label(text, Palette.TEXT_DIM)
	heading.add_theme_font_size_override("font_size", 16)
	return heading


## A right-aligned number (or column header) for a grid.
func _make_value(text: String, color: Color) -> Label:
	var label := _make_label(text, color)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return label


func _score(run: Dictionary) -> Dictionary:
	return _as_dict(run.get("score", {}))


func _as_dict(value: Variant) -> Dictionary:
	if value is Dictionary:
		return value
	return {}


## A number from a parsed JSON dictionary; missing or non-numeric values read as 0.
func _num(source: Dictionary, key: String) -> float:
	var value: Variant = source.get(key, 0.0)
	if value is float or value is int:
		return float(value)
	return 0.0


## 1234567 -> "1,234,567" (values under 1000 unchanged).
func _grouped(value: float) -> String:
	var whole: int = roundi(value)
	var digits: String = str(absi(whole))
	var out := ""
	for i: int in range(digits.length()):
		if i > 0 and (digits.length() - i) % 3 == 0:
			out += ","
		out += digits.substr(i, 1)
	return ("-" if whole < 0 else "") + out


## An explicit sign for a difference: "+1,234", "-2", "0".
func _signed(value: int) -> String:
	if value > 0:
		return "+" + _grouped(float(value))
	return _grouped(float(value))


## Seconds as m:ss.
func _mss(seconds: float) -> String:
	var total: int = maxi(0, floori(seconds))
	var minutes: int = floori(float(total) / 60.0)
	return "%d:%02d" % [minutes, total - minutes * 60]
