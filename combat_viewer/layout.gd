extends Node
## The window's draggable layout: the map against the macro column against the info panel, and all of them
## against the transport and the scrub bar below. Each boundary is a split container's bar; where it stands
## is kept as shares of the window, one set for the Takes layout and one for Situations, and written to
## `user://combat_viewer.cfg` with the tab last chosen (not when the viewer runs headless: a check must
## neither read nor leave a person's layout). `reset` puts the defaults back, `toggle_info` folds the info
## panel away.

const Palette := preload("res://palette.gd")

const FILE := "user://combat_viewer.cfg"
const TAKES := "takes"
const SITUATIONS := "situations"
## Shares of the window: the macro column and the info panel of its width (the map has the rest), the
## transport and scrub bar of its height. Takes: the proportions the viewer had before it could be dragged.
const DEFAULTS: Dictionary = {
	"takes": {"debug": 0.16, "info": 0.24, "bottom": 0.13, "info_shown": true},
	"situations": {"debug": 0.22, "info": 0.18, "bottom": 0.13, "info_shown": true},
}
const SETTLE_FRAMES := 3  # a bar's place is corrected over a few frames (its offset is relative to a rest place)

var mode: String = TAKES
var _shares: Dictionary = {}
var _config: ConfigFile = ConfigFile.new()
var _persist: bool = false
var _window: Control
var _rows: SplitContainer  # everything above | the transport and the scrub bar
var _outer: SplitContainer  # the map and the macro column | the info panel
var _inner: SplitContainer  # the map | the macro column
var _debug: Control
var _info: Control
var _applying: bool = false
var _again: bool = false


func setup(window: Control, rows: SplitContainer, outer: SplitContainer, inner: SplitContainer, debug: Control, info: Control) -> void:
	_window = window
	_rows = rows
	_outer = outer
	_inner = inner
	_debug = debug
	_info = info
	_persist = DisplayServer.get_name() != "headless"
	if _persist:
		_config.load(FILE)
	for name: String in DEFAULTS:
		var found: Dictionary = (DEFAULTS[name] as Dictionary).duplicate()
		for key: String in found:
			found[key] = _config.get_value(name, key, found[key])
		_shares[name] = found
	for split: SplitContainer in [_rows, _outer, _inner]:
		split.dragged.connect(_on_dragged)
	_window.resized.connect(apply)


## The tab chosen when the viewer was last closed ("" when none was kept).
func kept_tab() -> String:
	return str(_config.get_value("window", "tab", "")) if _persist else ""


func keep_tab(name: String) -> void:
	_config.set_value("window", "tab", name)
	_save()


## Lay the window out for `name` (TAKES or SITUATIONS) by its kept shares.
func use(name: String) -> void:
	mode = name
	apply()


func share(key: String) -> float:
	return float((_shares[mode] as Dictionary)[key])


func info_shown() -> bool:
	return bool((_shares[mode] as Dictionary)["info_shown"])


## The defaults again for the layout in use.
func reset() -> void:
	_shares[mode] = (DEFAULTS[mode] as Dictionary).duplicate()
	_store()
	apply()


## Fold the info panel away, or bring it back.
func toggle_info() -> void:
	(_shares[mode] as Dictionary)["info_shown"] = not info_shown()
	_store()
	apply()


## Put every bar where the shares say. A bar's offset counts from where the container would rest it, so the
## place is measured and corrected over a few frames.
func apply() -> void:
	if _window == null or not _window.is_inside_tree():
		return
	if _applying:
		_again = true
		return
	_applying = true
	_info.visible = info_shown()
	for i: int in range(SETTLE_FRAMES):
		var width: float = _window.size.x
		var height: float = _window.size.y
		var info: float = share("info") * width if _info.visible else 0.0
		var debug: float = share("debug") * width if _debug.visible else 0.0
		_place(_rows, height * (1.0 - share("bottom")), true)
		_place(_outer, width - info, false)
		_place(_inner, width - info - debug, false)
		await get_tree().process_frame
	_applying = false
	if _again:
		_again = false
		apply()


func _place(split: SplitContainer, wanted: float, vertical: bool) -> void:
	var first: Control = split.get_child(0)
	var second: Control = split.get_child(1)
	if not first.visible or not second.visible:
		return
	var now: float = first.size.y if vertical else first.size.x
	split.split_offset += roundi(wanted - now)


## A bar was dragged: the shares as they stand now, kept.
func _on_dragged(_offset: int) -> void:
	if _applying:
		return
	var width: float = maxf(_window.size.x, 1.0)
	var found: Dictionary = _shares[mode]
	if _info.visible:
		found["info"] = clampf(_info.size.x / width, 0.05, 0.7)
	if _debug.visible:
		found["debug"] = clampf(_debug.size.x / width, 0.05, 0.6)
	var bottom: Control = _rows.get_child(1)
	found["bottom"] = clampf(bottom.size.y / maxf(_window.size.y, 1.0), 0.05, 0.6)
	_store()


func _store() -> void:
	var found: Dictionary = _shares[mode]
	for key: String in found:
		_config.set_value(mode, key, found[key])
	_save()


func _save() -> void:
	if _persist:
		_config.save(FILE)
