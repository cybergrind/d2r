extends SceneTree
## Drives the whole viewer without a person: opens the scene on a directory of exported takes, opens
## each listed take in turn, and presses every key the README names while it plays.
## `godot --headless --path combat_viewer --script res://tests/drive.gd -- <directory>`; a script error
## shows as a SCRIPT ERROR line in the output, and the last line says what state the viewer ended in.

const KEYS: Array[int] = [
	KEY_SPACE, KEY_RIGHT, KEY_RIGHT, KEY_LEFT, KEY_BRACKETRIGHT, KEY_BRACKETRIGHT, KEY_BRACKETRIGHT, KEY_N, KEY_N,
	KEY_L, KEY_N, KEY_P, KEY_L, KEY_TAB, KEY_N, KEY_V, KEY_F, KEY_HOME, KEY_F, KEY_V, KEY_BRACKETLEFT, KEY_TAB,
	KEY_SPACE, KEY_ESCAPE, KEY_ESCAPE, KEY_SPACE,
]


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var scene: PackedScene = load("res://main.tscn")
	var main: Control = scene.instantiate()
	root.add_child(main)
	await _frames(5)
	var directory: String = main.directory
	var index: Variant = JSON.parse_string(FileAccess.get_file_as_string(directory.path_join("index.json")))
	if typeof(index) != TYPE_DICTIONARY:
		print("no index in ", directory)
		quit(1)
		return
	var takes: Array = index["takes"]
	for item: Variant in takes:
		var take: Dictionary = item
		main._on_take_chosen(directory.path_join(str(take["file"])))
		await _frames(3)
		var trace: PackedStringArray = PackedStringArray()
		for keycode: int in KEYS:
			var event: InputEventKey = InputEventKey.new()
			event.keycode = keycode as Key
			event.pressed = true
			Input.parse_input_event(event)
			await _frames(12)
			trace.append("%s>%d %s%s%s%s%s m%d %sx" % [
				OS.get_keycode_string(keycode), main.tick, main.policy_name, " play" if main.playing else "",
				" overlay" if main.overlay else "", " follow" if main.camera["follow"] else "",
				" loop" if main.looping else "", main.moment_index, str(main.SPEEDS[main.speed_index]),
			])
		print("  ".join(trace))
		print("list shown after Esc, Esc, Space: %s" % main._list.visible)
		main._list.visible = false
		main._on_seek_requested(main.data.end - 20)
		main.playing = true
		await _frames(40)
		print("%s: tick %d of %d, policy %s, overlay %s, moment %d of %d, playing %s" % [
			main.data.take, main.tick, main.data.end, main.policy_name, main.overlay, main.moment_index,
			main._moments.size(), main.playing
		])
	quit(0)


func _frames(count: int) -> void:
	for i: int in range(count):
		await process_frame
