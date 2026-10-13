extends HBoxContainer
## The strip above the take list that says which folder of exported files it shows: "Takes" (recorded
## fights, `viz/`), "Stance" (the step comparisons, `viz-stance/`, when that folder exists) and
## "Situations" (test situations played in the arena, `viz-situations/`: always there, the viewer asks the
## situations' exporter for the list and for each file). Emits `chosen` with the tab's name.

signal chosen(name: String)

const Palette := preload("res://palette.gd")

var _buttons: Dictionary = {}  # name -> Button
var _group: ButtonGroup = ButtonGroup.new()


## Show a tab for each of `names`, `current` pressed.
func set_tabs(names: PackedStringArray, current: String) -> void:
	for child: Node in get_children():
		child.queue_free()
	_buttons.clear()
	for name: String in names:
		var button: Button = Button.new()
		button.text = name
		button.toggle_mode = true
		button.button_group = _group
		button.focus_mode = Control.FOCUS_NONE
		button.custom_minimum_size = Vector2(110, 0)
		button.set_pressed_no_signal(name == current)
		button.pressed.connect(func() -> void: chosen.emit(name))
		add_child(button)
		_buttons[name] = button


func choose(name: String) -> void:
	var button: Button = _buttons.get(name)
	if button != null:
		button.set_pressed_no_signal(true)
