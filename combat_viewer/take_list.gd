extends PanelContainer
## The opening screen of the replay viewer: a full-size list of recorded fights ("takes") read from
## the index the main script loaded. Each take shows how much each attack policy gained over the
## player's recorded casts. Double-click or Enter on a row emits take_chosen with the take's file path.
## Built entirely in code; no scene file.

signal take_chosen(path: String)  ## the full path of the take's file
signal browse_requested  ## the user wants to choose another folder

const Palette := preload("res://palette.gd")

const COL_TAKE := 0
const COL_AREA := 1
const COL_LENGTH := 2
const COL_CASTS := 3
const COL_KILLS := 4
const COL_RECORDED := 5
const COL_FIRST_POLICY := 6  # one gain column per policy follows, then Gate, Moments, Size

const DASH := "–"
const THIN_SPACE := " "
const HINT := "Double-click or Enter opens a take. Click a column title to sort. Gain: life the policy's casts took per combat second over the recorded casts."
const BYTES_PER_MB := 1000000.0

var _takes: Array[Dictionary] = []
var _policies: Array[String] = []
var _directory: String = ""
var _has_problem: bool = false
var _problem: String = ""
var _sort_column: int = -1
var _sort_descending: bool = true

var _status: Label
var _tree: Tree
var _browse_button: Button


## Fills the list with the takes of `index`, replacing whatever was shown before.
func show_index(index: Dictionary, directory: String) -> void:
	_takes.clear()
	_policies.clear()
	_directory = directory
	_has_problem = false
	_problem = ""

	var raw: Variant = index.get("takes")
	if raw is Array:
		for entry in raw as Array:
			if entry is Dictionary:
				_takes.append(entry as Dictionary)

	if not _takes.is_empty():
		var runs: Variant = _takes[0].get("runs")
		if runs is Dictionary:
			for key in (runs as Dictionary).keys():
				var policy: String = str(key)
				if policy != "recorded":
					_policies.append(policy)
		_policies.sort_custom(_policy_before)

	_sort_column = COL_FIRST_POLICY if not _policies.is_empty() else -1
	_sort_descending = true
	_refresh()


## Shows `text` in place of the list (no usable index). The "Choose folder" button stays usable.
func show_problem(text: String) -> void:
	_takes.clear()
	_policies.clear()
	_directory = ""
	_has_problem = true
	_problem = text
	_sort_column = -1
	_refresh()


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL

	var box := StyleBoxFlat.new()
	box.bg_color = Palette.BACKGROUND
	box.set_content_margin_all(24)
	add_theme_stylebox_override("panel", box)

	var column := VBoxContainer.new()
	add_child(column)

	var title := Label.new()
	title.text = "Recorded fights"
	title.add_theme_font_size_override("font_size", 30)
	title.add_theme_color_override("font_color", Palette.TEXT)
	column.add_child(title)

	_status = _dim_label()
	column.add_child(_status)

	_tree = Tree.new()
	_tree.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_tree.hide_root = true
	_tree.column_titles_visible = true
	_tree.select_mode = Tree.SELECT_ROW
	_tree.column_title_clicked.connect(_on_column_title_clicked)
	_tree.item_activated.connect(_on_item_activated)
	column.add_child(_tree)

	var bottom := HBoxContainer.new()
	column.add_child(bottom)

	var hint := _dim_label()
	hint.text = HINT
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom.add_child(hint)

	_browse_button = Button.new()
	_browse_button.text = "Choose folder…"
	_browse_button.pressed.connect(_on_browse_pressed)
	bottom.add_child(_browse_button)

	_refresh()


func _dim_label() -> Label:
	var label := Label.new()
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_color_override("font_color", Palette.TEXT_DIM)
	return label


## Re-sorts the takes and rebuilds the columns and rows. Does nothing before _ready.
func _refresh() -> void:
	if _tree == null:
		return
	_takes.sort_custom(_is_before)
	if _has_problem:
		_status.text = _problem
	else:
		var count: int = _takes.size()
		_status.text = "%s: %d %s" % [_directory, count, "take" if count == 1 else "takes"]
	_rebuild_columns()
	_rebuild_rows()


func _rebuild_columns() -> void:
	var titles: Array[String] = ["Take", "Area", "Length", "Casts", "Kills", "Recorded /s"]
	for policy in _policies:
		titles.append("%s gain" % policy)
	titles.append("Gate")
	titles.append("Moments")
	titles.append("Size")

	_tree.columns = titles.size()
	for column in range(titles.size()):
		_tree.set_column_title(column, titles[column])
		_tree.set_column_expand(column, column <= COL_AREA)
		var minimum: int = 0
		if column == COL_TAKE:
			minimum = 240
		elif column == COL_AREA:
			minimum = 200
		_tree.set_column_custom_minimum_width(column, minimum)
		var alignment: HorizontalAlignment = HORIZONTAL_ALIGNMENT_RIGHT if _is_numeric(column) else HORIZONTAL_ALIGNMENT_LEFT
		_tree.set_column_title_alignment(column, alignment)


func _rebuild_rows() -> void:
	_tree.clear()
	var root: TreeItem = _tree.create_item()
	for take in _takes:
		var row: TreeItem = _tree.create_item(root)
		var recorded: Dictionary = _run(take, "recorded")

		row.set_metadata(COL_TAKE, _text(take.get("file"), ""))
		row.set_text(COL_TAKE, _text(take.get("take"), "?"))
		row.set_text(COL_AREA, _text(take.get("area_name"), "?"))
		row.set_text(COL_LENGTH, _format_length(take.get("seconds")))
		row.set_text(COL_CASTS, _format_int(recorded.get("casts")))
		row.set_text(COL_KILLS, _format_int(recorded.get("kills")))
		row.set_text(COL_RECORDED, _format_thousands(recorded.get("placement_per_combat_second")))

		for index in range(_policies.size()):
			var gain_column: int = COL_FIRST_POLICY + index
			var gain: Variant = _run(take, _policies[index]).get("gain")
			row.set_text(gain_column, _format_gain(gain))
			row.set_custom_color(gain_column, _gain_color(gain))

		var gate_column: int = _gate_column()
		var gate: Variant = _gate_value(take)
		row.set_text(gate_column, DASH if gate == null else ("pass" if float(gate) > 0.5 else "fail"))
		var gate_color: Color = Palette.GOOD if gate != null and float(gate) > 0.5 else Palette.TEXT_DIM
		row.set_custom_color(gate_column, gate_color)

		row.set_text(_moments_column(), _format_moments(take))
		row.set_text(_size_column(), _format_size(take.get("bytes")))

		for column in range(_column_count()):
			if _is_numeric(column):
				row.set_text_alignment(column, HORIZONTAL_ALIGNMENT_RIGHT)


func _on_column_title_clicked(column: int, mouse_button_index: int) -> void:
	if mouse_button_index != MOUSE_BUTTON_LEFT:
		return
	if column == _sort_column:
		_sort_descending = not _sort_descending
	else:
		_sort_column = column
		_sort_descending = column >= COL_LENGTH
	_refresh()


func _on_item_activated() -> void:
	var item: TreeItem = _tree.get_selected()
	if item == null:
		return
	var file: String = _text(item.get_metadata(COL_TAKE), "")
	if file.is_empty():
		return
	take_chosen.emit(_directory.path_join(file))


func _on_browse_pressed() -> void:
	browse_requested.emit()


# Column layout

func _gate_column() -> int:
	return COL_FIRST_POLICY + _policies.size()


func _moments_column() -> int:
	return _gate_column() + 1


func _size_column() -> int:
	return _gate_column() + 2


func _column_count() -> int:
	return _size_column() + 1


func _is_numeric(column: int) -> bool:
	return column != COL_TAKE and column != COL_AREA and column != _gate_column()


# Sorting

func _is_before(a: Dictionary, b: Dictionary) -> bool:
	var value_a: Variant = _sort_value(a, _sort_column)
	var value_b: Variant = _sort_value(b, _sort_column)
	if value_a == null and value_b == null:
		return _name_of(a) < _name_of(b)
	if value_a == null:
		return false  # nulls sort last
	if value_b == null:
		return true
	if value_a == value_b:
		return _name_of(a) < _name_of(b)
	if _sort_descending:
		return value_a > value_b
	return value_a < value_b


func _sort_value(take: Dictionary, column: int) -> Variant:
	var recorded: Dictionary = _run(take, "recorded")
	if column == COL_TAKE:
		return _text_or_null(take.get("take"))
	if column == COL_AREA:
		return _text_or_null(take.get("area_name"))
	if column == COL_LENGTH:
		return _number_or_null(take.get("seconds"))
	if column == COL_CASTS:
		return _number_or_null(recorded.get("casts"))
	if column == COL_KILLS:
		return _number_or_null(recorded.get("kills"))
	if column == COL_RECORDED:
		return _number_or_null(recorded.get("placement_per_combat_second"))
	if column == _gate_column():
		return _gate_value(take)
	if column == _moments_column():
		if _policies.is_empty():
			return null
		return _number_or_null(_moments_for(take, _policies[0]))
	if column == _size_column():
		return _number_or_null(take.get("bytes"))
	var index: int = column - COL_FIRST_POLICY
	if index >= 0 and index < _policies.size():
		return _number_or_null(_run(take, _policies[index]).get("gain"))
	return null


## Policies in the order live, yield, then the rest alphabetically.
func _policy_before(a: String, b: String) -> bool:
	var rank_a: int = _policy_rank(a)
	var rank_b: int = _policy_rank(b)
	if rank_a != rank_b:
		return rank_a < rank_b
	return a < b


func _policy_rank(policy: String) -> int:
	if policy == "live":
		return 0
	if policy == "yield":
		return 1
	return 2


# Reading the index

func _run(take: Dictionary, run_name: String) -> Dictionary:
	var runs: Variant = take.get("runs")
	if runs is Dictionary:
		var run: Variant = (runs as Dictionary).get(run_name)
		if run is Dictionary:
			return run as Dictionary
	return {}


func _moments_for(take: Dictionary, policy: String) -> Variant:
	var moments: Variant = take.get("moments")
	if moments is Dictionary:
		return (moments as Dictionary).get(policy)
	return null


## 1.0 when the gate passed, 0.0 when it failed, null when the index does not say.
func _gate_value(take: Dictionary) -> Variant:
	var gate: Variant = take.get("gate_passes")
	if gate == null:
		return null
	return 1.0 if bool(gate) else 0.0


func _name_of(take: Dictionary) -> String:
	return _text(take.get("take"), "")


func _text(value: Variant, fallback: String) -> String:
	if value == null:
		return fallback
	return str(value)


func _text_or_null(value: Variant) -> Variant:
	if value == null:
		return null
	return str(value)


func _number_or_null(value: Variant) -> Variant:
	if value == null or not (value is int or value is float):
		return null
	return float(value)


# Formatting

func _format_length(seconds: Variant) -> String:
	if seconds == null:
		return DASH
	var total: int = roundi(float(seconds))
	var minutes: int = floori(float(total) / 60.0)
	var rest: int = total - minutes * 60
	return "%d:%02d" % [minutes, rest]


func _format_int(value: Variant) -> String:
	if value == null:
		return DASH
	return str(roundi(float(value)))


func _format_thousands(value: Variant) -> String:
	if value == null:
		return DASH
	var number: int = roundi(float(value))
	var digits: String = str(absi(number))
	var grouped: String = ""
	var count: int = 0
	for i in range(digits.length() - 1, -1, -1):
		if count > 0 and count % 3 == 0:
			grouped = THIN_SPACE + grouped
		grouped = digits[i] + grouped
		count += 1
	return ("-" if number < 0 else "") + grouped


func _format_gain(gain: Variant) -> String:
	if gain == null:
		return DASH
	var percent: float = float(gain) * 100.0
	var sign_text: String = "+" if percent >= 0.0 else ""
	return "%s%.1f%%" % [sign_text, percent]


func _gain_color(gain: Variant) -> Color:
	if gain == null:
		return Palette.TEXT_DIM
	var value: float = float(gain)
	if value > 0.0:
		return Palette.GOOD
	if value < 0.0:
		return Palette.BAD
	return Palette.TEXT_DIM


func _format_moments(take: Dictionary) -> String:
	if _policies.is_empty():
		return DASH
	return _format_int(_moments_for(take, _policies[0]))


func _format_size(bytes: Variant) -> String:
	if bytes == null:
		return DASH
	return "%.2f MB" % (float(bytes) / BYTES_PER_MB)

