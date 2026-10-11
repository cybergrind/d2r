extends PanelContainer
## The opening screen of the replay viewer: a full-size list of recorded fights ("takes"): the ones in
## the index the main script loaded, and every other take in the folder the index was exported from
## (`source`), which has nothing to play yet. Each exported take shows how much each attack policy
## gained over the player's recorded casts. Double-click or Enter on a row emits take_chosen with the
## take's file path, or export_requested when the take has no file; E asks for the export of any row,
## R for the folder to be read again.
## Built entirely in code; no scene file.

signal take_chosen(path: String)  ## the full path of the take's file
signal browse_requested  ## the user wants to choose another folder
signal refresh_requested  ## the user wants the folder read again (R)
## the user wants this take exported (again): its directory, and the policies to run (none: the default)
signal export_requested(take_directory: String, policies: PackedStringArray)

const Palette := preload("res://palette.gd")

const COL_TAKE := 0
const COL_AREA := 1
const COL_LENGTH := 2
const COL_CASTS := 3
const COL_KILLS := 4
const COL_RECORDED := 5
const COL_FIRST_POLICY := 6  # one gain column per policy follows, then Gate, Moments, Size, Export

const DASH := "–"
const THIN_SPACE := " "
const HINT := "Double-click or Enter opens a take (exports it first when it has no file). E exports the chosen take again, R reads the folder again. Click a column title to sort. Gain: life the policy's casts took per combat second over the recorded casts."
const NOT_EXPORTED := "not exported"
const MANIFEST := "manifest.json"
const FRAMES: Array[String] = ["frames.jsonl", "frames.jsonl.gz"]
const BYTES_PER_MB := 1000000.0

var _takes: Array[Dictionary] = []
var _policies: Array[String] = []
var _directory: String = ""
var _source: String = ""  # the folder of take directories, "" when the index names none
var _export_state: Dictionary = {}  # take name -> what its export is doing or how it failed
var _rows: Dictionary = {}  # take name -> TreeItem
var _has_problem: bool = false
var _problem: String = ""
var _sort_column: int = COL_TAKE
var _sort_descending: bool = true

var _status: Label
var _tree: Tree
var _browse_button: Button
var _export_button: Button
var _export_new_button: Button


## Fills the list with the takes of `index` and the other takes in its source folder, replacing
## whatever was shown before. The same folder shown again keeps its order and the chosen take.
func show_index(index: Dictionary, directory: String) -> void:
	var same: bool = directory == _directory and not _has_problem
	var chosen: String = _chosen_take()
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

	_source = _source_of(index, directory)
	var left_out: Variant = index.get("left_out")
	_takes.append_array(_not_exported(left_out as Dictionary if left_out is Dictionary else {}))

	if not same:
		_export_state.clear()
		_sort_column = COL_TAKE
		_sort_descending = true
	_refresh()
	_choose(chosen)


## What the export of `take` is doing ("2/6 policy live"), or how it failed; "" when there is nothing to say.
func set_export_state(take: String, text: String) -> void:
	if text.is_empty():
		_export_state.erase(take)
	else:
		_export_state[take] = text
	var row: TreeItem = _rows.get(take)
	if row != null:
		_show_export(row, _take_named(take))


## Shows `text` in place of the list (no usable index). The "Choose folder" button stays usable.
func show_problem(text: String) -> void:
	_takes.clear()
	_policies.clear()
	_directory = ""
	_source = ""
	_has_problem = true
	_problem = text
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
	_tree.allow_search = false  # letters are keys here (E), not a search of the first column
	_tree.item_selected.connect(_refresh_buttons)
	_tree.column_title_clicked.connect(_on_column_title_clicked)
	_tree.item_activated.connect(_on_item_activated)
	column.add_child(_tree)

	var bottom := HBoxContainer.new()
	column.add_child(bottom)

	var hint := _dim_label()
	hint.text = HINT
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom.add_child(hint)

	_export_new_button = Button.new()
	_export_new_button.text = "Export new"
	_export_new_button.tooltip_text = "Export every take that was never tried"
	_export_new_button.pressed.connect(_export_new)
	bottom.add_child(_export_new_button)

	_export_button = Button.new()
	_export_button.text = "Export chosen (E)"
	_export_button.tooltip_text = "Run the exporter again for the chosen take"
	_export_button.pressed.connect(_export_chosen)
	bottom.add_child(_export_button)

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
		var exported: int = 0
		for take in _takes:
			if _is_exported(take):
				exported += 1
		_status.text = "%s: %d %s" % [_directory, count, "take" if count == 1 else "takes"]
		if exported < count:
			_status.text += ", %d exported; the others are in %s" % [exported, _source]
	_rebuild_columns()
	_rebuild_rows()
	_refresh_buttons()


func _rebuild_columns() -> void:
	var titles: Array[String] = ["Take", "Area", "Length", "Casts", "Kills", "Recorded /s"]
	for policy in _policies:
		titles.append("%s gain" % policy)
	titles.append("Gate")
	titles.append("Moments")
	titles.append("Size")
	titles.append("Export")

	_tree.columns = titles.size()
	for column in range(titles.size()):
		_tree.set_column_title(column, titles[column])
		_tree.set_column_expand(column, column <= COL_AREA)
		var minimum: int = 0
		if column == COL_TAKE:
			minimum = 220
		elif column == COL_AREA:
			minimum = 170
		elif column == titles.size() - 1:
			minimum = 190  # room for a stage ("5/6 policy yield") or why a take has no file
		_tree.set_column_custom_minimum_width(column, minimum)
		var alignment: HorizontalAlignment = HORIZONTAL_ALIGNMENT_RIGHT if _is_numeric(column) else HORIZONTAL_ALIGNMENT_LEFT
		_tree.set_column_title_alignment(column, alignment)


func _rebuild_rows() -> void:
	_tree.clear()
	_rows.clear()
	var root: TreeItem = _tree.create_item()
	for take in _takes:
		var row: TreeItem = _tree.create_item(root)
		var recorded: Dictionary = _run(take, "recorded")
		_rows[_name_of(take)] = row

		row.set_metadata(COL_TAKE, _name_of(take))
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
		if not _is_exported(take):
			for column in range(_export_column()):
				row.set_custom_color(column, Palette.TEXT_DIM)
		_show_export(row, take)


## The Export cell of `take`'s row: what its export is doing, else why it has no file.
func _show_export(row: TreeItem, take: Dictionary) -> void:
	var text: String = _text(_export_state.get(_name_of(take)), "")
	if text.is_empty() and not _is_exported(take):
		text = _text(take.get("why"), NOT_EXPORTED)
	row.set_text(_export_column(), text)
	row.set_custom_color(_export_column(), Palette.TEXT_DIM)


func _on_column_title_clicked(column: int, mouse_button_index: int) -> void:
	if mouse_button_index != MOUSE_BUTTON_LEFT:
		return
	if column == _sort_column:
		_sort_descending = not _sort_descending
	else:
		_sort_column = column
		_sort_descending = column >= COL_LENGTH or column == COL_TAKE
	var chosen: String = _chosen_take()
	_refresh()
	_choose(chosen)


func _on_item_activated() -> void:
	var take: Dictionary = _take_named(_chosen_take())
	if take.is_empty():
		return
	if _is_exported(take):
		take_chosen.emit(_directory.path_join(_text(take.get("file"), "")))
	else:
		_export(take)


func _unhandled_key_input(event: InputEvent) -> void:
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo or not is_visible_in_tree():
		return
	if key.keycode == KEY_E:
		_export_chosen()
		get_viewport().set_input_as_handled()
	elif key.keycode == KEY_R:
		refresh_requested.emit()
		get_viewport().set_input_as_handled()


# Exporting

func _export_chosen() -> void:
	_export(_take_named(_chosen_take()))


## Every take nobody tried to export yet (not the ones the exporter left out).
func _export_new() -> void:
	for take in _takes:
		if not _is_exported(take) and take.get("why") == null:
			_export(take)


func _export(take: Dictionary) -> void:
	if take.is_empty() or _source.is_empty():
		return
	var policies: PackedStringArray = PackedStringArray()
	var runs: Variant = take.get("runs")
	if runs is Dictionary:
		for key in (runs as Dictionary).keys():
			if str(key) != "recorded":
				policies.append(str(key))
	export_requested.emit(_source.path_join(_name_of(take)), policies)


func _refresh_buttons() -> void:
	_export_button.disabled = _source.is_empty() or _chosen_take().is_empty()
	var fresh: bool = false
	for take in _takes:
		if not _is_exported(take) and take.get("why") == null:
			fresh = true
	_export_new_button.disabled = _source.is_empty() or not fresh


# The chosen row

func _chosen_take() -> String:
	var item: TreeItem = _tree.get_selected() if _tree != null else null
	return "" if item == null else _text(item.get_metadata(COL_TAKE), "")


func _choose(take: String) -> void:
	var row: TreeItem = _rows.get(take)
	if row == null:
		return
	row.select(COL_TAKE)
	_tree.scroll_to_item(row)
	_refresh_buttons()


func _take_named(take: String) -> Dictionary:
	for found in _takes:
		if _name_of(found) == take:
			return found
	return {}


func _on_browse_pressed() -> void:
	browse_requested.emit()


# Column layout

func _gate_column() -> int:
	return COL_FIRST_POLICY + _policies.size()


func _moments_column() -> int:
	return _gate_column() + 1


func _size_column() -> int:
	return _gate_column() + 2


func _export_column() -> int:
	return _gate_column() + 3


func _column_count() -> int:
	return _export_column() + 1


func _is_numeric(column: int) -> bool:
	return column != COL_TAKE and column != COL_AREA and column != _gate_column() and column != _export_column()


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
	if column == COL_TAKE:  # by when it was recorded; the name, which starts with that, when unknown
		var started: Variant = take.get("started_at")
		return _text_or_null(take.get("take") if started == null else started)
	if column == _export_column():
		return _text_or_null(null if _is_exported(take) else take.get("why", NOT_EXPORTED))
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

func _is_exported(take: Dictionary) -> bool:
	return not _text(take.get("file"), "").is_empty()


## The folder the index's takes were exported from: the one it names, else (an index written before
## it named one) the folder above when a listed take is a directory there. "" when neither.
func _source_of(index: Dictionary, directory: String) -> String:
	var named: String = _text(index.get("source"), "")
	if not named.is_empty():
		return named if DirAccess.dir_exists_absolute(named) else ""
	var above: String = directory.get_base_dir()
	for take in _takes:
		if FileAccess.file_exists(above.path_join(_name_of(take)).path_join(MANIFEST)):
			return above
	return ""


## A row for every take directory in the source folder the index does not list, from its manifest:
## when, where and how long, and why the exporter left it out when it said.
func _not_exported(left_out: Dictionary) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	if _source.is_empty():
		return out
	var listed: Dictionary = {}
	var area_names: Dictionary = {}
	for take in _takes:
		listed[_name_of(take)] = true
		area_names[take.get("area")] = take.get("area_name")
	for name in DirAccess.get_directories_at(_source):
		var path: String = _source.path_join(name)
		if listed.has(name) or not FRAMES.any(func(file: String) -> bool: return FileAccess.file_exists(path.path_join(file))):
			continue
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path.path_join(MANIFEST)))
		var manifest: Dictionary = parsed as Dictionary if parsed is Dictionary else {}
		var area: Variant = manifest.get("area")
		var row: Dictionary = {
			"take": name,
			"area": area,
			"area_name": area_names.get(area, DASH if area == null else "area %d" % int(area)),
			"started_at": manifest.get("started_at"),
			"seconds": manifest.get("seconds"),
		}
		if left_out.has(name):
			row["why"] = str(left_out[name])
		out.append(row)
	return out


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

