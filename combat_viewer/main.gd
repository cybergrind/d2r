extends Control
## The viewer's window: the take list, then one take played back with the recorded run and a policy
## run in step (two views side by side, or one with both overlaid), the scrub bar and the side panel.
##
## Arguments after `--` on the command line: a directory of exported takes or one take's .json, then
## optionally `--tick=N`, `--policy=NAME`, `--overlay`, `--fit`, `--play`, and `--shot=FILE.png` (save a picture
## of the window and quit: how the viewer is checked without a person at it).

const Palette := preload("res://palette.gd")
const TakeData := preload("res://take_data.gd")
const MapView := preload("res://map_view.gd")
const TimelineBar := preload("res://timeline_bar.gd")
const SidePanel := preload("res://side_panel.gd")
const TakeList := preload("res://take_list.gd")
const Exporter := preload("res://exporter.gd")

const DEFAULT_DIRECTORY := "../inventory_tracking/runs/combat/viz"
const INDEX := "index.json"
const SPEEDS: Array[float] = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
const LEAD_TICKS := 25  # a jump to a moment lands a second before it
const SHOT_FRAMES := 8  # frames drawn before `--shot` saves the picture

var data: RefCounted = null
var directory: String = ""
var tick_f: float = 0.0
var tick: int = -1
var playing: bool = false
var speed_index: int = 2
var policy_name: String = "live"
var overlay: bool = false
var looping: bool = false
var moment_index: int = -1
var camera: Dictionary = {"center": Vector2.ZERO, "zoom": 1.1, "follow": true}

var _moments: Array = []
var _recorded: Dictionary = {}
var _policy: Dictionary = {}
var _left: Control
var _right: Control
var _timeline: Control
var _panel: PanelContainer
var _list: PanelContainer
var _exporter: Node
var _dialog: FileDialog
var _play_button: Button
var _speed_label: Label
var _time_label: Label
var _policy_button: OptionButton
var _overlay_button: CheckButton
var _follow_button: CheckButton
var _shot_path: String = ""
var _shot_countdown: int = -1
var _fit_pending: bool = false


func _ready() -> void:
	_build()
	var wanted: Dictionary = _arguments()
	var target: String = wanted.get("path", "")
	if target.is_empty():
		target = ProjectSettings.globalize_path("res://").path_join(DEFAULT_DIRECTORY).simplify_path()
	if target.get_extension() == "json" and target.get_file() != INDEX:
		directory = target.get_base_dir()
		_open_take(target)
	else:
		_open_directory(target)
	if data != null:
		if wanted.has("policy"):
			_choose_policy(str(wanted["policy"]))
		if wanted.has("overlay"):
			_set_overlay(true)
		if wanted.has("tick"):
			_seek(int(wanted["tick"]))
		if wanted.has("play"):
			playing = true
		if wanted.has("fit"):
			_fit_pending = true
	if wanted.has("shot"):
		_shot_path = str(wanted["shot"])
		_shot_countdown = SHOT_FRAMES
	_refresh_transport()


## The user arguments: the first bare one is the path, `--name=value` and `--name` the options.
func _arguments() -> Dictionary:
	var out: Dictionary = {}
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--"):
			var parts: PackedStringArray = argument.substr(2).split("=", true, 1)
			out[parts[0]] = parts[1] if parts.size() > 1 else ""
		elif not out.has("path"):
			out["path"] = argument
	return out


func _build() -> void:
	var background: ColorRect = ColorRect.new()
	background.color = Palette.BACKGROUND
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)

	var column: VBoxContainer = VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.add_theme_constant_override("separation", 4)
	add_child(column)

	var middle: HBoxContainer = HBoxContainer.new()
	middle.size_flags_vertical = Control.SIZE_EXPAND_FILL
	middle.add_theme_constant_override("separation", 4)
	column.add_child(middle)

	_left = MapView.new()
	_right = MapView.new()
	for view: Control in [_left, _right]:
		view.camera = camera
		view.camera_changed.connect(_on_camera_changed)
		middle.add_child(view)

	_panel = SidePanel.new()
	_panel.moment_chosen.connect(_on_moment_chosen)
	_panel.loop_toggled.connect(_on_loop_toggled)
	middle.add_child(_panel)

	var transport: HBoxContainer = HBoxContainer.new()
	transport.add_theme_constant_override("separation", 10)
	column.add_child(transport)
	transport.add_child(_button("Takes", _show_list))
	transport.add_child(_button("|<", func() -> void: _step(-1)))
	_play_button = _button("Play", _toggle_play)
	_play_button.custom_minimum_size = Vector2(90, 0)
	transport.add_child(_play_button)
	transport.add_child(_button(">|", func() -> void: _step(1)))
	transport.add_child(_button("slower", func() -> void: _change_speed(-1)))
	_speed_label = _label("1x", Palette.TEXT)
	_speed_label.custom_minimum_size = Vector2(60, 0)
	_speed_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	transport.add_child(_speed_label)
	transport.add_child(_button("faster", func() -> void: _change_speed(1)))
	_time_label = _label("", Palette.TEXT)
	_time_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	transport.add_child(_time_label)
	transport.add_child(_label("policy", Palette.POLICY))
	_policy_button = OptionButton.new()
	_policy_button.focus_mode = Control.FOCUS_NONE
	_policy_button.item_selected.connect(_on_policy_selected)
	transport.add_child(_policy_button)
	_overlay_button = CheckButton.new()
	_overlay_button.text = "overlaid"
	_overlay_button.focus_mode = Control.FOCUS_NONE
	_overlay_button.toggled.connect(_set_overlay)
	transport.add_child(_overlay_button)
	_follow_button = CheckButton.new()
	_follow_button.text = "follow"
	_follow_button.focus_mode = Control.FOCUS_NONE
	_follow_button.set_pressed_no_signal(true)
	_follow_button.toggled.connect(_set_follow)
	transport.add_child(_follow_button)
	transport.add_child(_button("fit", _fit))

	_timeline = TimelineBar.new()
	_timeline.seek_requested.connect(_on_seek_requested)
	column.add_child(_timeline)

	_list = TakeList.new()
	_list.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_list.take_chosen.connect(_on_take_chosen)
	_list.browse_requested.connect(_browse)
	_list.export_requested.connect(_on_export_requested)
	_list.refresh_requested.connect(_show_list)
	add_child(_list)

	_exporter = Exporter.new()
	_exporter.progressed.connect(_on_export_progressed)
	_exporter.finished.connect(_on_export_finished)
	add_child(_exporter)

	_dialog = FileDialog.new()
	_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_dialog.file_mode = FileDialog.FILE_MODE_OPEN_DIR
	_dialog.title = "The directory the takes were exported to (it holds index.json)"
	_dialog.dir_selected.connect(_open_directory)
	add_child(_dialog)


func _button(text: String, pressed: Callable) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE
	button.pressed.connect(pressed)
	return button


func _label(text: String, color: Color) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.add_theme_color_override("font_color", color)
	return label


## Show the takes listed in `path`'s index.json, or say why not.
func _open_directory(path: String) -> void:
	directory = path
	_list.visible = true
	var file: String = path.path_join(INDEX)
	if not FileAccess.file_exists(file):
		_list.show_problem(
			"No %s in %s. Export the takes first (make combat-viz), or choose the folder they are in." % [INDEX, path]
		)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(file))
	if typeof(parsed) != TYPE_DICTIONARY:
		_list.show_problem("%s is not an index written by inventory_tracking.combat.viz." % file)
		return
	var index: Dictionary = parsed
	_list.show_index(index, path)


func _browse() -> void:
	_dialog.current_dir = directory if DirAccess.dir_exists_absolute(directory) else OS.get_environment("HOME")
	_dialog.popup_centered_ratio(0.6)


func _on_take_chosen(path: String) -> void:
	_open_take(path)


func _on_export_requested(take_directory: String, policies: PackedStringArray) -> void:
	var take: String = take_directory.get_file()
	if _exporter.is_pending(take):
		return
	_list.set_export_state(take, "waiting")
	_exporter.request(take_directory, directory, policies)


func _on_export_progressed(take: String, done: int, total: int, stage: String) -> void:
	_list.set_export_state(take, "%d/%d %s" % [done, total, stage])


## The exporter rewrote the index: show it again, with what went wrong on the take's row if it failed.
func _on_export_finished(take: String, ok: bool, message: String) -> void:
	_list.set_export_state(take, "" if ok else "failed: %s" % message)
	if _list.visible:
		_open_directory(directory)


func _open_take(path: String) -> void:
	var loaded: RefCounted = TakeData.load_file(path)
	if not loaded.problem.is_empty():
		_list.visible = true
		_list.show_problem(loaded.problem)
		return
	data = loaded
	_list.visible = false
	_recorded = data.runs[0]
	var names: PackedStringArray = data.policy_names()
	_policy_button.clear()
	for name: String in names:
		_policy_button.add_item(name)
	if not names.has(policy_name) and not names.is_empty():
		policy_name = names[0]
	var gate: Dictionary = data.gate
	var fails: Array = gate.get("fails", [])
	var trust: String = "the simulator reproduces this take (gate passes)"
	if not bool(gate.get("passes", false)):
		trust = "the simulator does not reproduce this take well (gate fails: %s)" % ", ".join(PackedStringArray(fails))
	_panel.set_take(
		"%s, %s" % [data.take, data.area_name],
		"%s long, %d monsters, %d recorded kills; %s" % [
			_clock(data.seconds), data.monsters.size(), data.recorded_kills.size(), trust
		]
	)
	_timeline.set_range(data.start, data.end)
	_timeline.set_running(data.player_run)
	playing = false
	looping = false
	_panel.set_loop(false)
	tick = -1
	tick_f = float(data.start)
	camera["follow"] = true
	_follow_button.set_pressed_no_signal(true)
	camera["zoom"] = 1.1
	_choose_policy(policy_name)
	_seek(data.start)
	_refresh_transport()


## Compare the recorded run with the policy run called `name`.
func _choose_policy(name: String) -> void:
	if data == null:
		return
	_policy = data.run_named(name)
	policy_name = _policy["name"]
	var names: PackedStringArray = data.policy_names()
	_policy_button.select(maxi(names.find(policy_name), 0))
	_moments = data.moments_of(policy_name)
	moment_index = -1
	var relative: Array = []
	var spans: PackedInt32Array = PackedInt32Array()
	for item: Variant in _moments:
		var moment: Dictionary = item
		var copy: Dictionary = moment.duplicate()
		copy["first"] = int(moment.get("first", 0)) - data.start
		copy["last"] = int(moment.get("last", 0)) - data.start
		relative.append(copy)
		spans.append(int(moment.get("first", 0)))
		spans.append(int(moment.get("last", 0)))
	_panel.set_runs(_recorded, _policy)
	_panel.set_moments(relative)
	_timeline.set_moments(spans, -1)
	_timeline.set_loop(-1, -1)
	var recorded_casts: PackedInt32Array = _recorded["cast_ticks"]
	var policy_casts: PackedInt32Array = _policy["cast_ticks"]
	var recorded_deaths: PackedInt32Array = _recorded["death_ticks"]
	var policy_deaths: PackedInt32Array = _policy["death_ticks"]
	_timeline.set_marks(recorded_casts, policy_casts, recorded_deaths, policy_deaths)
	_timeline.set_moves(_recorded["moves"], _policy["moves"])
	_show_runs()
	_show_tick(true)


func _show_runs() -> void:
	if data == null:
		return
	var both: Array[Dictionary] = [_recorded, _policy]
	var both_colors: Array[Color] = [Palette.RECORDED, Palette.POLICY]
	if overlay:
		_left.show_runs(data, both, both_colors)
		_right.visible = false
	else:
		var one: Array[Dictionary] = [_recorded]
		var one_color: Array[Color] = [Palette.RECORDED]
		var other: Array[Dictionary] = [_policy]
		var other_color: Array[Color] = [Palette.POLICY]
		_left.show_runs(data, one, one_color)
		_right.show_runs(data, other, other_color)
		_right.visible = true


func _process(delta: float) -> void:
	if _fit_pending:
		_fit_pending = false
		_left.fit()
	if data != null and playing:
		tick_f += delta * data.rate * SPEEDS[speed_index]
		if looping and moment_index >= 0:
			var moment: Dictionary = _moments[moment_index]
			var first: float = maxf(float(moment["first"]) - LEAD_TICKS, data.start)
			var last: float = minf(float(moment["last"]) + LEAD_TICKS, data.end)
			if tick_f > last or tick_f < first:
				tick_f = first
		if tick_f >= float(data.end):
			tick_f = float(data.end)
			playing = false
			_refresh_transport()
		_show_tick(false)
	if _shot_countdown >= 0:
		_shot_countdown -= 1
		if _shot_countdown < 0:
			_save_shot()


## Put everything at the current tick; with `force` even when the tick did not change.
func _show_tick(force: bool) -> void:
	if data == null:
		return
	var now: int = clampi(floori(tick_f), data.start, data.end)
	if now == tick and not force:
		return
	tick = now
	_follow_character()
	_left.set_tick(tick)
	_right.set_tick(tick)
	_timeline.set_tick(tick)
	var elapsed: float = float(tick - data.start) / data.rate
	_panel.set_totals(elapsed, data.totals(_recorded, tick), data.totals(_policy, tick))
	var moving: String = "  (the player is moving)" if TakeData.in_spans(data.player_run, tick) else ""
	_time_label.text = "%s / %s   tick %d%s" % [_clock(elapsed), _clock(data.seconds), tick, moving]


## Follow: each side-by-side view centres on its own run's character, the overlay on the policy's.
func _follow_character() -> void:
	_left.shift = Vector2.ZERO
	_right.shift = Vector2.ZERO
	if not camera["follow"]:
		return
	if overlay:
		camera["center"] = data.character_at(_policy, tick)
		return
	var mine: Vector2 = data.character_at(_recorded, tick)
	camera["center"] = mine
	_right.shift = data.character_at(_policy, tick) - mine


func _clock(seconds: float) -> String:
	var whole: int = maxi(floori(seconds), 0)
	return "%d:%02d.%d" % [whole / 60, whole % 60, floori((seconds - floorf(seconds)) * 10.0)]


func _seek(to: int) -> void:
	if data == null:
		return
	tick_f = float(clampi(to, data.start, data.end))
	_show_tick(true)


func _step(ticks: int) -> void:
	playing = false
	_seek(tick + ticks)
	_refresh_transport()


func _toggle_play() -> void:
	if data == null:
		return
	if not playing and tick >= data.end:
		_seek(data.start)
	playing = not playing
	_refresh_transport()


func _change_speed(by: int) -> void:
	speed_index = clampi(speed_index + by, 0, SPEEDS.size() - 1)
	_refresh_transport()


func _refresh_transport() -> void:
	_play_button.text = "Pause" if playing else "Play"
	_speed_label.text = "%sx" % str(SPEEDS[speed_index])


func _set_overlay(on: bool) -> void:
	overlay = on
	_overlay_button.set_pressed_no_signal(on)
	_show_runs()
	_show_tick(true)


func _set_follow(on: bool) -> void:
	camera["follow"] = on
	_follow_button.set_pressed_no_signal(on)
	_show_tick(true)


func _fit() -> void:
	_left.fit()


func _on_camera_changed() -> void:
	var follow: bool = camera["follow"]
	if not follow:
		_left.shift = Vector2.ZERO
		_right.shift = Vector2.ZERO
	_follow_button.set_pressed_no_signal(follow)
	_left.queue_redraw()
	_right.queue_redraw()


func _on_seek_requested(to: int) -> void:
	_seek(to)


func _on_policy_selected(index: int) -> void:
	_choose_policy(_policy_button.get_item_text(index))


func _next_policy(by: int) -> void:
	if data == null:
		return
	var names: PackedStringArray = data.policy_names()
	if names.is_empty():
		return
	var index: int = posmod(names.find(policy_name) + by, names.size())
	_choose_policy(names[index])


func _on_moment_chosen(index: int) -> void:
	_go_to_moment(index)


## Jump to a moment: a second before it, playing.
func _go_to_moment(index: int) -> void:
	if data == null or _moments.is_empty():
		return
	moment_index = posmod(index, _moments.size())
	var moment: Dictionary = _moments[moment_index]
	_panel.select_moment(moment_index)
	var spans: PackedInt32Array = PackedInt32Array()
	for item: Variant in _moments:
		var found: Dictionary = item
		spans.append(int(found["first"]))
		spans.append(int(found["last"]))
	_timeline.set_moments(spans, moment_index)
	_show_loop()
	_seek(int(moment["first"]) - LEAD_TICKS)
	playing = true
	_refresh_transport()


## The moment after (`by` 1) or before (-1) the current tick.
func _step_moment(by: int) -> void:
	if _moments.is_empty():
		return
	var target: int = -1
	if by > 0:
		for i: int in range(_moments.size()):
			var moment: Dictionary = _moments[i]
			if int(moment["first"]) - LEAD_TICKS > tick and i != moment_index:
				target = i
				break
		if target < 0:
			target = 0
	else:
		for i: int in range(_moments.size() - 1, -1, -1):
			var moment: Dictionary = _moments[i]
			if int(moment["first"]) < tick - 2 * LEAD_TICKS and i != moment_index:
				target = i
				break
		if target < 0:
			target = _moments.size() - 1
	_go_to_moment(target)


func _on_loop_toggled(on: bool) -> void:
	looping = on
	_show_loop()


func _show_loop() -> void:
	if looping and moment_index >= 0:
		var moment: Dictionary = _moments[moment_index]
		_timeline.set_loop(
			maxi(int(moment["first"]) - LEAD_TICKS, data.start), mini(int(moment["last"]) + LEAD_TICKS, data.end)
		)
	else:
		_timeline.set_loop(-1, -1)


func _show_list() -> void:
	playing = false
	_refresh_transport()
	if directory.is_empty():
		return
	_open_directory(directory)


func _input(event: InputEvent) -> void:
	if not event is InputEventKey:
		return
	var key: InputEventKey = event
	if not key.pressed or _dialog.visible:
		return
	if _list.visible:
		if key.keycode == KEY_ESCAPE and data != null and not key.echo:
			_list.visible = false
			get_viewport().set_input_as_handled()
		return
	var handled: bool = true
	match key.keycode:
		KEY_SPACE:
			if not key.echo:
				_toggle_play()
		KEY_LEFT:
			_step(-roundi(data.rate) if key.shift_pressed else -1)
		KEY_RIGHT:
			_step(roundi(data.rate) if key.shift_pressed else 1)
		KEY_BRACKETLEFT:
			_change_speed(-1)
		KEY_BRACKETRIGHT:
			_change_speed(1)
		KEY_TAB:
			if not key.echo:
				_next_policy(-1 if key.shift_pressed else 1)
		KEY_N:
			_step_moment(1)
		KEY_P:
			_step_moment(-1)
		KEY_L:
			if not key.echo:
				looping = not looping
				_panel.set_loop(looping)
				_show_loop()
		KEY_V:
			if not key.echo:
				_set_overlay(not overlay)
		KEY_F:
			if not key.echo:
				_set_follow(not camera["follow"])
		KEY_HOME:
			_fit()
		KEY_ESCAPE:
			_show_list()
		_:
			handled = false
	if handled:
		get_viewport().set_input_as_handled()


## Save what the window shows to `--shot`'s file and quit.
func _save_shot() -> void:
	var image: Image = get_viewport().get_texture().get_image()
	var result: Error = image.save_png(_shot_path)
	print("shot %s: %s" % [_shot_path, "saved" if result == OK else "failed (%d)" % result])
	get_tree().quit(0 if result == OK else 1)
