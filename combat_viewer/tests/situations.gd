extends SceneTree
## The Situations tab driven without a person, from a cold start: the tab is chosen (the viewer asks the
## situations' exporter for the catalog), a situation is asked for as a double-click on its row does (the
## viewer runs its export and opens it), the timeline is stepped and the debug panel read back at two
## times (the task, the macro's line, the life, the death's banner), every variant is flipped through
## with Tab, and E plays it again. With `--take=<name>` a recorded take of the Takes folder is opened
## as well and its task readout printed (its sidecar `<name>.tasks.json`, written if it is missing).
## `godot --headless --path combat_viewer --script res://tests/situations.gd [-- --situation=four-packs --take=<take>]`
## A script error shows as a SCRIPT ERROR line; the last line is `situations: ok` or says what failed.

const WAIT_FRAMES := 3600  # frames an export is waited for

var main: Control


func _init() -> void:
	_run.call_deferred()


func _option(name: String, fallback: String) -> String:
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--%s=" % name):
			return argument.split("=", true, 1)[1]
	return fallback


func _fail(why: String) -> void:
	print("situations: FAILED: ", why)
	quit(1)


func _run() -> void:
	var scene: PackedScene = load("res://main.tscn")
	main = scene.instantiate()
	root.size = Vector2i(2000, 1125)  # a headless window is 64 x 64 otherwise: no layout to measure
	root.add_child(main)
	await _frames(5)
	print("tabs: ", main._tabs.get_child_count(), ", shown first: ", main.source)
	main._choose_source(main.SITUATIONS)
	await _frames(3)
	var directory: String = main.directory
	var index: Variant = JSON.parse_string(FileAccess.get_file_as_string(directory.path_join("index.json")))
	if typeof(index) != TYPE_DICTIONARY:
		_fail("no index in %s after the tab was chosen" % directory)
		return
	var rows: Array = index["takes"]
	for item: Variant in rows:
		var row: Dictionary = item
		print("  %s | %s | %s" % [row["take"], row.get("file", row.get("why", "not exported")), row["area_name"]])
	var wanted: String = _option("situation", "four-packs")
	var source: String = str(index["source"])
	main.data = null
	main._on_export_requested(source.path_join(wanted), PackedStringArray())
	if not await _opened(wanted):
		_fail("%s was not opened after its export: %s" % [wanted, main._list._export_state])
		return
	var data: RefCounted = main.data
	print("opened %s: %d ticks, %d runs, %d monsters" % [data.take, data.end, data.runs.size(), data.monsters.size()])
	await _layout_check(true)
	var names: PackedStringArray = data.policy_names()
	var banners: int = 0
	for name: String in names:
		main._choose_policy(name)
		var debug: PanelContainer = main._debug
		if not debug.visible:
			_fail("the run %s shows no debug panel" % name)
			return
		print("-- ", name)
		for at: int in [5, data.end / 4, data.end - 1]:
			main._on_seek_requested(at)
			await _frames(2)
			print("   tick %d: %s | %s | %s | %s | line: %s%s" % [
				main.tick, debug.mode_text(main.tick), debug.task_text(main.tick), debug.key_text(main.tick),
				debug.life_text(main.tick), debug.line_text(debug.current_line(main.tick)),
				"" if debug.banner_text(main.tick).is_empty() else " | " + debug.banner_text(main.tick),
			])
		if not debug.banner_text(data.end).is_empty():
			banners += 1
	print("variants with a death banner at the end: %d of %d" % [banners, names.size()])
	for keycode: int in [KEY_SPACE, KEY_TAB, KEY_RIGHT, KEY_V, KEY_F, KEY_HOME, KEY_V, KEY_SPACE]:
		_press(keycode)
		await _frames(6)
	# E: the situation played again and shown again.
	_press(KEY_E)
	await _frames(2)
	if not main._exporter.is_pending(wanted):
		_fail("E did not ask for the export of %s" % wanted)
		return
	main.data = null
	if not await _opened(wanted):
		_fail("%s was not opened again after E" % wanted)
		return
	print("E: played again and opened, tick %d" % main.tick)
	var take: String = _option("take", "")
	if not take.is_empty():
		await _take(take)
	print("situations: ok")
	quit(0)


## The split layout as it stands: the panes' widths, one map or two, the info panel folded and back, the reset.
func _layout_check(situation: bool) -> void:
	await _frames(8)
	var width: float = main.size.x
	var debug: Control = main._debug
	var info: Control = main._situation if situation else main._panel
	print("layout %s: window %d x %d, map %d, macro column %d (%s), info %d (%s), bottom %d; maps shown: %d; titles plain: %s" % [
		main._layout.mode, int(width), int(main.size.y), int(main._left.get_parent().size.x), int(debug.size.x),
		"shown" if debug.visible else "hidden", int(info.size.x), info.get_script().resource_path.get_file(),
		int(main._timeline.get_parent().size.y), 1 + int(main._right.visible), main._left.plain_titles,
	])
	if situation:
		var names: PackedStringArray = main.data.policy_names()
		print("   rows of the situation panel: %d; the take tables shown: %s" % [main._situation.row_count(), main._panel.visible])
		print("   first variant, tick 0: %s | %s | %s" % [debug.mode_text(0), debug.task_text(0), debug.life_text(0)])
		if names.size() > 1:
			main._choose_policy(names[1])
			_press(KEY_V)
			await _frames(4)
			print("   V on the second variant: maps shown %d (left %s | right %s)" % [
				1 + int(main._right.visible), main._left.shown[0]["label"], main._right.shown[0]["label"]])
			main._choose_policy(names[0])
			await _frames(2)
			print("   V on the first variant: maps shown %d" % (1 + int(main._right.visible)))
			_press(KEY_V)
			await _frames(2)
	_press(KEY_I)
	await _frames(8)
	print("   I: info panel %s, map %d" % ["shown" if info.get_parent().visible else "folded", int(main._left.get_parent().size.x)])
	_press(KEY_I)
	main._layout._shares[main._layout.mode]["info"] = 0.4
	main._layout.apply()
	await _frames(8)
	var wide: int = int(info.size.x)
	_press(KEY_0)
	await _frames(8)
	print("   info at a 0.4 share: %d; after 0 (reset): %d" % [wide, int(info.size.x)])


## A recorded take with its task sidecar: the readout at two times.
func _take(take: String) -> void:
	main._choose_source(main.TAKES)
	await _frames(3)
	var file: String = main.directory.path_join(take + ".json")
	if not FileAccess.file_exists(file):
		print("take %s is not exported in %s: its readout is not checked" % [take, main.directory])
		return
	if not FileAccess.file_exists(main.directory.path_join(take + ".tasks.json")):
		var source: String = str(JSON.parse_string(FileAccess.get_file_as_string(main.directory.path_join("index.json")))["source"])
		main._exporter._queue.append({"take": take, "source": source.path_join(take), "out": main.directory,
			"policies": PackedStringArray(), "module": main._exporter.SITUATIONS, "tasks": true})
		main._exporter._start_next()
		for i: int in range(WAIT_FRAMES):
			await process_frame
			if not main._exporter.is_pending(take):
				break
	main._on_take_chosen(file)
	await _frames(3)
	var debug: PanelContainer = main._debug
	print("take %s: debug panel %s" % [take, "shown" if debug.visible else "hidden (no sidecar)"])
	await _layout_check(false)
	for at: int in [main.data.start + 1900, main.data.start + 2300]:
		main._on_seek_requested(at)
		await _frames(2)
		print("   tick %d: %s | %s | %s | line: %s" % [
			main.tick, debug.mode_text(main.tick), debug.task_text(main.tick), debug.key_text(main.tick),
			debug.line_text(debug.current_line(main.tick)),
		])


func _opened(take: String) -> bool:
	for i: int in range(WAIT_FRAMES):
		await process_frame
		OS.delay_msec(10)
		if main.data != null and main.data.take == take and not main._list.visible:
			return true
		var state: String = str(main._list._export_state.get(take, ""))
		if state.begins_with("failed"):
			return false
	return false


func _press(keycode: int) -> void:
	var event: InputEventKey = InputEventKey.new()
	event.keycode = keycode as Key
	event.pressed = true
	Input.parse_input_event(event)


func _frames(count: int) -> void:
	for i: int in range(count):
		await process_frame
