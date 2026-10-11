extends SceneTree
## The take list and the exporter without a person: opens the scene on a directory of exported takes,
## prints how many takes the list shows and the first rows in its order, then exports the named take
## through the viewer and prints each stage it hears and how the row ends up.
## `godot --headless --path combat_viewer --script res://tests/export.gd -- <directory> --take=<name>`

const WAIT_FRAMES := 6000


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var scene: PackedScene = load("res://main.tscn")
	var main: Control = scene.instantiate()
	root.add_child(main)
	await _frames(5)
	var list: PanelContainer = main._list
	var exported: int = 0
	for take: Dictionary in list._takes:
		if list._is_exported(take):
			exported += 1
	print("%d takes listed, %d exported, source %s" % [list._takes.size(), exported, list._source])
	for take: Dictionary in list._takes.slice(0, 5):
		print("  %s  %s" % [take["take"], list._rows[take["take"]].get_text(list._export_column())])
	var wanted: String = ""
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--take="):
			wanted = argument.trim_prefix("--take=")
	if wanted.is_empty():
		quit(0)
		return
	var ended: Array = []
	main._exporter.progressed.connect(
		func(take: String, done: int, total: int, stage: String) -> void: print("  %s %d/%d %s" % [take, done, total, stage])
	)
	main._exporter.finished.connect(func(take: String, ok: bool, message: String) -> void: ended.append([take, ok, message]))
	list._export(list._take_named(wanted))
	for i: int in range(WAIT_FRAMES):
		if not ended.is_empty():
			break
		await process_frame
	if ended.is_empty():
		print("the export of %s did not end" % wanted)
		quit(1)
		return
	await _frames(2)
	print("ended: %s" % str(ended[0]))
	var row: TreeItem = list._rows.get(wanted)
	print("row: exported %s, export cell '%s'" % [
		list._is_exported(list._take_named(wanted)), "" if row == null else row.get_text(list._export_column()),
	])
	quit(0 if ended[0][1] else 1)


func _frames(count: int) -> void:
	for i: int in range(count):
		await process_frame
