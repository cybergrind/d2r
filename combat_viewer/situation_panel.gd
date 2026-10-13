extends PanelContainer
## The info panel of a situation (README.md, "Situations"), in place of the take comparison's tables: one
## row a variant with what it came to: died (when, to what) or survived, cleared or what was left, the life
## lost and the least life, potions, kills, strikes, the way gone, and each boss of the route (how near the
## character came, when it died). A click on a row chooses that variant, as Tab does.
## Built entirely in code; no scene file.

signal variant_chosen(name: String)

const Palette := preload("res://palette.gd")

var _title: Label
var _rows: VBoxContainer
var _buttons: Dictionary = {}  # run name -> Button


func _ready() -> void:
	custom_minimum_size = Vector2(240, 0)
	var box := StyleBoxFlat.new()
	box.bg_color = Palette.PANEL
	box.set_content_margin_all(10)
	add_theme_stylebox_override("panel", box)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	add_child(column)
	_title = Label.new()
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.add_theme_color_override("font_color", Palette.TEXT)
	_title.add_theme_font_size_override("font_size", 16)
	column.add_child(_title)
	var hint := Label.new()
	hint.text = "Tab / click: a variant · V: beside the first · E: play again · I: fold this panel · 0: layout reset"
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_color_override("font_color", Palette.TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 12)
	column.add_child(hint)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(scroll)
	_rows = VBoxContainer.new()
	_rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_rows.add_theme_constant_override("separation", 4)
	scroll.add_child(_rows)


## A row for each variant of `runs` (the take's runs but its first, which is the first variant again).
func set_runs(title: String, runs: Array[Dictionary]) -> void:
	_title.text = title
	for child: Node in _rows.get_children():
		child.queue_free()
	_buttons.clear()
	for run: Dictionary in runs:
		if not run["policy"]:
			continue
		var name: String = run["name"]
		var button: Button = Button.new()
		button.text = row_text(run)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.focus_mode = Control.FOCUS_NONE
		button.toggle_mode = true
		button.add_theme_font_size_override("font_size", 13)
		button.pressed.connect(func() -> void: variant_chosen.emit(name))
		_rows.add_child(button)
		_buttons[name] = button


func choose(name: String) -> void:
	for found: String in _buttons:
		(_buttons[found] as Button).set_pressed_no_signal(found == name)


func row_count() -> int:
	return _buttons.size()


## What a variant came to, in a few lines.
static func row_text(run: Dictionary) -> String:
	var name: String = run["name"]
	var summary: Dictionary = run.get("summary", {})
	if summary.is_empty():
		return name
	var lines: PackedStringArray = PackedStringArray([name])
	var died: Variant = summary.get("died")
	if typeof(died) == TYPE_DICTIONARY:
		lines.append("DIED at %.1f s: %s" % [float((died as Dictionary)["at"]), str((died as Dictionary)["cause"])])
	else:
		var cleared: Variant = summary.get("cleared_at")
		lines.append("survived, %s" % (
			"cleared at %.1f s" % float(cleared) if cleared != null else "%d hostiles left" % int(summary.get("alive", 0))
		))
	lines.append("life lost %d, least %d · potions %d · kills %d/%d · strikes %d · moved %d" % [
		int(summary.get("lost", 0)), int(summary.get("low", 0)), int(summary.get("potions", 0)),
		int(summary.get("kills", 0)), int(summary.get("hostiles", 0)), int(summary.get("strikes", 0)),
		int(summary.get("moved", 0)),
	])
	var goals: Array = summary.get("goals", [])
	for goal: Variant in goals:
		lines.append(str(goal))
	return "\n".join(lines)
