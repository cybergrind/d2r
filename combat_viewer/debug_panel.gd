extends PanelContainer
## What the macro was doing at the playback time, for a run that carries a debug track (README.md,
## "Situations"): the task (attack mode on or off, the routine working and what it is after, the sweep's
## steps left, the last key and what became of it), the character's life with the potions drunk so far,
## the last blow that took life, the macro's lines scrolling with the time (the current one chosen), and a
## banner from the tick the character died at. Hidden for a run without a track (an ordinary take).
## Built entirely in code; no scene file.

const Palette := preload("res://palette.gd")

const WIDTH := 260.0
const NOT_RECORDED := "task: not recorded (a take before schema 4)"

var _lines: Array = []  # [tick, text]
var _line_ticks: PackedInt32Array = PackedInt32Array()
var _presses: Array = []  # [tick, key, what became of it]
var _press_ticks: PackedInt32Array = PackedInt32Array()
var _tasks: Array = []  # [tick, {attack, routine, working, what, sweep}]
var _task_ticks: PackedInt32Array = PackedInt32Array()
var _has_tasks: bool = false
var _hurts: Array = []  # [tick, points, type, kind]
var _hurt_ticks: PackedInt32Array = PackedInt32Array()
var _potion_ticks: PackedInt32Array = PackedInt32Array()
var _life: Dictionary = {"t": PackedInt32Array(), "v": PackedInt32Array()}
var _max_life: int = 0
var _death_tick: int = -1
var _death_cause: String = ""
var _rate: float = 25.0
var _start: int = 0
var _shown_line: int = -2

var _mode_label: Label
var _task_label: Label
var _key_label: Label
var _life_label: Label
var _life_bar: ProgressBar
var _hurt_label: Label
var _banner: Label
var _list: RichTextLabel


func _ready() -> void:
	custom_minimum_size = Vector2(WIDTH, 0)
	var box := StyleBoxFlat.new()
	box.bg_color = Palette.PANEL
	box.border_color = Palette.PANEL_EDGE
	box.set_border_width_all(1)
	box.set_content_margin_all(10)
	add_theme_stylebox_override("panel", box)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	add_child(column)
	_banner = _label("", Palette.LIFE, 20)
	_banner.visible = false
	column.add_child(_banner)
	_mode_label = _label("", Palette.TEXT, 22)
	column.add_child(_mode_label)
	_task_label = _label("", Palette.TEXT, 16)
	column.add_child(_task_label)
	_key_label = _label("", Palette.TEXT_DIM, 14)
	column.add_child(_key_label)
	_life_label = _label("", Palette.TEXT, 16)
	column.add_child(_life_label)
	_life_bar = ProgressBar.new()
	_life_bar.show_percentage = false
	_life_bar.custom_minimum_size = Vector2(0, 10)
	var fill := StyleBoxFlat.new()
	fill.bg_color = Palette.LIFE
	_life_bar.add_theme_stylebox_override("fill", fill)
	column.add_child(_life_bar)
	_hurt_label = _label("", Palette.BAD, 14)
	column.add_child(_hurt_label)
	column.add_child(_label("What the macro said", Palette.TEXT_DIM, 14))
	# Every line whole: wrapped to the column's width, the current one bright and in view.
	_list = RichTextLabel.new()
	_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.focus_mode = Control.FOCUS_NONE
	_list.bbcode_enabled = false
	_list.scroll_following = false
	_list.add_theme_font_size_override("normal_font_size", 13)
	column.add_child(_list)
	visible = false


func _label(text: String, color: Color, font_size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_color_override("font_color", color)
	label.add_theme_font_size_override("font_size", font_size)
	return label


## Whether `run` carries a debug track.
static func has_debug(run: Dictionary) -> bool:
	return not (run.get("debug", {}) as Dictionary).is_empty()


## Show the debug track of `run` (hidden when it has none); `rate` ticks a second from tick `start`.
func show_run(run: Dictionary, rate: float, start: int) -> void:
	var debug: Dictionary = run.get("debug", {})
	visible = not debug.is_empty()
	_rate = rate
	_start = start
	_lines = _rows(debug.get("lines"))
	_line_ticks = _ticks(_lines)
	_presses = _rows(debug.get("presses"))
	_press_ticks = _ticks(_presses)
	_has_tasks = typeof(debug.get("tasks")) == TYPE_ARRAY
	_tasks = _rows(debug.get("tasks"))
	_task_ticks = _ticks(_tasks)
	_hurts = _rows(debug.get("hurts"))
	_hurt_ticks = _ticks(_hurts)
	_potion_ticks = _ticks(_rows(debug.get("potions")))
	_life = _steps(debug.get("life"))
	_max_life = int(debug.get("max_life", 0))
	var death: Variant = debug.get("death")
	_death_tick = -1
	_death_cause = ""
	if typeof(death) == TYPE_DICTIONARY:
		_death_tick = int((death as Dictionary).get("tick", -1))
		_death_cause = str((death as Dictionary).get("cause", ""))
	_shown_line = -2


## The ticks of the presses and of the blows, and the death's tick, for the scrub bar's marks.
func press_ticks() -> PackedInt32Array:
	return _press_ticks


func hurt_ticks() -> PackedInt32Array:
	return _hurt_ticks


func death_tick() -> int:
	return _death_tick


## The character's life as a step series and the most it holds; empty when the track has none.
func life_series() -> Dictionary:
	return _life


func max_life() -> int:
	return _max_life


func set_tick(tick: int) -> void:
	if not visible or _mode_label == null:
		return
	_mode_label.text = mode_text(tick)
	_mode_label.add_theme_color_override("font_color", Palette.GOOD if attack_on(tick) else Palette.BAD)
	_task_label.text = task_text(tick)
	_key_label.text = key_text(tick)
	_life_label.text = life_text(tick)
	_life_label.visible = _max_life > 0
	_life_bar.visible = _max_life > 0
	if _max_life > 0:
		_life_bar.max_value = _max_life
		_life_bar.value = _life_at(tick)
	_hurt_label.text = hurt_text(tick)
	_banner.text = banner_text(tick)
	_banner.visible = not _banner.text.is_empty()
	var index: int = current_line(tick)
	if index != _shown_line:
		_shown_line = index
		_write_lines(index)


## The macro's lines, a paragraph each, the one at `current` bright; scrolled so it is in view.
func _write_lines(current: int) -> void:
	_list.clear()
	for i: int in range(_lines.size()):
		var line: Array = _lines[i]
		_list.push_color(Palette.TEXT if i == current else Palette.TEXT_DIM)
		_list.add_text("%s  %s" % [_seconds(int(line[0])), str(line[1])])
		_list.pop()
		if i < _lines.size() - 1:
			_list.newline()
	if current > 1:
		_list.scroll_to_paragraph(current - 1)


func _task_at(tick: int) -> Dictionary:
	var index: int = _task_ticks.bsearch(tick, false) - 1
	if index < 0:
		return {}
	var row: Array = _tasks[index]
	return row[1]


func attack_on(tick: int) -> bool:
	return bool(_task_at(tick).get("attack", false))


func mode_text(tick: int) -> String:
	if not _has_tasks:
		return ""
	return "ATTACK MODE ON" if attack_on(tick) else "ATTACK MODE OFF"


## The routine working at `tick` and what it is after, with the sweep's steps left when the track has them.
func task_text(tick: int) -> String:
	if not _has_tasks:
		return NOT_RECORDED
	var task: Dictionary = _task_at(tick)
	if task.is_empty():
		return "task: idle"
	var sweep: Variant = task.get("sweep")
	var steps: String = "" if sweep == null or int(sweep) <= 0 else "   sweep: %d steps left" % int(sweep)
	return "task: %s%s" % [str(task.get("what", "idle")), steps]


## The last key pressed up to `tick`, how long ago, and what became of it.
func key_text(tick: int) -> String:
	var index: int = _press_ticks.bsearch(tick, false) - 1
	if index < 0:
		return "no key pressed yet"
	var press: Array = _presses[index]
	var ago: float = float(tick - int(press[0])) / _rate
	var outcome: String = str(press[2])
	return "%s %.1f s ago%s   (%d presses so far)" % [str(press[1]), ago, "" if outcome.is_empty() else ": " + outcome, index + 1]


func _life_at(tick: int) -> int:
	var ticks: PackedInt32Array = _life["t"]
	var values: PackedInt32Array = _life["v"]
	var index: int = ticks.bsearch(tick, false) - 1
	return 0 if index < 0 else values[index]


func life_text(tick: int) -> String:
	if _max_life <= 0:
		return ""
	var life: int = _life_at(tick)
	return "life %d / %d (%d%%)   potions drunk: %d" % [
		life, _max_life, roundi(100.0 * life / _max_life), _potion_ticks.bsearch(tick, false)
	]


## The last blow that took life up to `tick`, while it is fresh (two seconds).
func hurt_text(tick: int) -> String:
	var index: int = _hurt_ticks.bsearch(tick, false) - 1
	if index < 0:
		return ""
	var hurt: Array = _hurts[index]
	var ago: float = float(tick - int(hurt[0])) / _rate
	if ago > 2.0:
		return ""
	return "-%d %s %s, %.1f s ago" % [int(hurt[1]), str(hurt[2]), str(hurt[3]), ago]


## "DEAD at T: cause" from the death's tick on; "" before it and in a run that lived.
func banner_text(tick: int) -> String:
	if _death_tick < 0 or tick < _death_tick:
		return ""
	return "DEAD at %s: %s" % [_seconds(_death_tick), _death_cause]


## The index of the macro's last line at or before `tick`; -1 before the first.
func current_line(tick: int) -> int:
	return _line_ticks.bsearch(tick, false) - 1


func line_text(index: int) -> String:
	if index < 0 or index >= _lines.size():
		return ""
	var line: Array = _lines[index]
	return str(line[1])


func _seconds(tick: int) -> String:
	return "%.1f s" % (float(tick - _start) / _rate)


func _rows(raw: Variant) -> Array:
	return raw as Array if typeof(raw) == TYPE_ARRAY else []


func _ticks(rows: Array) -> PackedInt32Array:
	var out: PackedInt32Array = PackedInt32Array()
	for item: Variant in rows:
		var row: Array = item
		out.append(int(row[0]))
	return out


func _steps(raw: Variant) -> Dictionary:
	var ticks: PackedInt32Array = PackedInt32Array()
	var values: PackedInt32Array = PackedInt32Array()
	if typeof(raw) == TYPE_ARRAY:
		var found: Array = raw
		for i: int in range(found.size() / 2):
			ticks.append(int(found[i * 2]))
			values.append(int(found[i * 2 + 1]))
	return {"t": ticks, "v": values}
