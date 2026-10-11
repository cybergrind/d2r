extends Control
## One isometric view of the level at a tick, for one run (side by side) or two (overlaid).
##
## The projection is the game's: across = x - y, down = x + y, a world unit 16 x 8 pixels at zoom 1.
## The camera (centre in world units, zoom, follow) is a Dictionary shared with the other view, so
## both show the same place; `camera_changed` tells the owner to redraw them.

signal camera_changed

const Palette := preload("res://palette.gd")
const TakeData := preload("res://take_data.gd")
const UNIT := Vector2(16.0, 8.0)
const ZOOM_MIN := 0.15
const ZOOM_MAX := 6.0
const FADE_TICKS := 50  # a death's cross fades over two seconds
const HOVER_PIXELS := 18.0
const TOGETHER := 1.0  # world units: overlaid characters closer than this are drawn as one
const BLADE_REACH := 22.1  # world units a blade flies out (mechanics/echoing_strike.py RANGE)

var data: RefCounted = null
var shown: Array[Dictionary] = []  # the runs drawn here: one, or two when overlaid
var colors: Array[Color] = []  # a colour per run in `shown`
var tick: int = 0
var shift: Vector2 = Vector2.ZERO  # added to the shared camera's centre: this view follows another character
var camera: Dictionary = {"center": Vector2.ZERO, "zoom": 1.1, "follow": true}

var _dragging: bool = false
var _hover: Vector2 = Vector2(-1, -1)


func _init() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_NONE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL


## Show `runs` of `take` (one or two), each in its colour.
func show_runs(take: RefCounted, runs: Array[Dictionary], run_colors: Array[Color]) -> void:
	data = take
	shown = runs
	colors = run_colors
	queue_redraw()


func set_tick(value: int) -> void:
	tick = value
	queue_redraw()


## The zoom and centre that put the whole level in this view.
func fit() -> void:
	if data == null:
		return
	var box: Rect2 = data.bounds
	if data.wall_texture != null:
		box = box.merge(data.wall_rect)
	var span: float = maxf(box.size.x + box.size.y, 1.0)
	var zoom: float = minf(size.x / (span * UNIT.x), size.y / (span * UNIT.y)) * 0.95
	camera["zoom"] = clampf(zoom, ZOOM_MIN, ZOOM_MAX)
	camera["center"] = box.get_center()
	camera["follow"] = false
	camera_changed.emit()


func _center() -> Vector2:
	var center: Vector2 = camera["center"]
	return center + shift


func _zoom() -> float:
	var zoom: float = camera["zoom"]
	return zoom


## A world point (file origin) on this control.
func to_screen(world: Vector2) -> Vector2:
	var center: Vector2 = _center()
	var d: Vector2 = world - center
	return size * 0.5 + Vector2((d.x - d.y) * UNIT.x, (d.x + d.y) * UNIT.y) * _zoom()


## The world point drawn at a point of this control.
func to_world(screen: Vector2) -> Vector2:
	var center: Vector2 = _center()
	var d: Vector2 = (screen - size * 0.5) / _zoom()
	var across: float = d.x / UNIT.x
	var down: float = d.y / UNIT.y
	return center + Vector2((across + down) * 0.5, (down - across) * 0.5)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button: InputEventMouseButton = event
		if button.button_index == MOUSE_BUTTON_WHEEL_UP and button.pressed:
			_zoom_at(button.position, 1.15)
			accept_event()
		elif button.button_index == MOUSE_BUTTON_WHEEL_DOWN and button.pressed:
			_zoom_at(button.position, 1.0 / 1.15)
			accept_event()
		elif button.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_MIDDLE, MOUSE_BUTTON_RIGHT]:
			_dragging = button.pressed
			accept_event()
	elif event is InputEventMouseMotion:
		var motion: InputEventMouseMotion = event
		_hover = motion.position
		if _dragging:
			var center: Vector2 = camera["center"]
			var d: Vector2 = motion.relative / _zoom()
			var across: float = d.x / UNIT.x
			var down: float = d.y / UNIT.y
			camera["center"] = center - Vector2((across + down) * 0.5, (down - across) * 0.5)
			camera["follow"] = false
			camera_changed.emit()
			accept_event()
		else:
			queue_redraw()


func _notification(what: int) -> void:
	if what == NOTIFICATION_MOUSE_EXIT:
		_hover = Vector2(-1, -1)
		_dragging = false
		queue_redraw()


func _zoom_at(point: Vector2, factor: float) -> void:
	var before: Vector2 = to_world(point)
	camera["zoom"] = clampf(_zoom() * factor, ZOOM_MIN, ZOOM_MAX)
	var after: Vector2 = to_world(point)
	var center: Vector2 = camera["center"]
	if not camera["follow"]:
		camera["center"] = center + before - after
	camera_changed.emit()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Palette.BACKGROUND)
	if data == null or shown.is_empty():
		return
	_draw_ground()
	_draw_pointer()
	_draw_companions()
	for i: int in range(shown.size()):
		_draw_moves(shown[i], colors[i])
	for i: int in range(shown.size()):
		_draw_casts(shown[i], colors[i])
	_draw_monsters()
	_draw_player()
	_draw_titles()
	draw_rect(Rect2(Vector2.ZERO, size), Palette.PANEL_EDGE, false, 1.0)


## The walls, the doors and the blades' reach, drawn in world units through the projection.
func _draw_ground() -> void:
	var zoom: float = _zoom()
	var projection: Transform2D = Transform2D(
		Vector2(UNIT.x, UNIT.y) * zoom, Vector2(-UNIT.x, UNIT.y) * zoom, to_screen(Vector2.ZERO)
	)
	draw_set_transform_matrix(projection)
	if data.wall_texture != null:
		draw_texture_rect(data.wall_texture, data.wall_rect, false)
	else:
		draw_rect(data.bounds.grow(4.0), Palette.FLOOR)
	var doors: Array[Dictionary] = data.doors
	for door: Dictionary in doors:
		var seen: PackedInt32Array = door["seen"]
		if not TakeData.in_spans(seen, tick):
			continue
		var at: Vector2 = door["at"]
		var half: float = door["r"]
		var box: Rect2 = Rect2(at - Vector2(half, half), Vector2(half, half) * 2.0)
		var closed: PackedInt32Array = door["closed"]
		if TakeData.in_spans(closed, tick):
			draw_rect(box, Color(Palette.DOOR_CLOSED, 0.75))
		else:
			draw_rect(box, Palette.DOOR_OPEN, false, 0.25)
	if TakeData.seen(data.player, tick) or tick >= data.start:
		for run: Dictionary in shown:
			var stand: Vector2 = data.character_at(run, tick)
			draw_arc(stand, BLADE_REACH, 0.0, TAU, 72, Color(Palette.TEXT_DIM, 0.28), 0.12)
			if not _own_paths():
				break
	draw_set_transform_matrix(Transform2D.IDENTITY)


func _draw_pointer() -> void:
	if not TakeData.seen(data.pointer, tick):
		return
	var at: Vector2 = to_screen(TakeData.position(data.pointer, tick))
	var color: Color = Color(Palette.POINTER, 0.7)
	draw_line(at - Vector2(9, 0), at + Vector2(9, 0), color, 2.0)
	draw_line(at - Vector2(0, 9), at + Vector2(0, 9), color, 2.0)


func _draw_companions() -> void:
	var radius: float = _body_radius() * 0.8
	var companions: Array[Dictionary] = data.companions
	for companion: Dictionary in companions:
		if not TakeData.seen(companion, tick):
			continue
		var at: Vector2 = to_screen(TakeData.position(companion, tick))
		draw_rect(Rect2(at - Vector2(radius, radius), Vector2(radius, radius) * 2.0), Palette.COMPANION)
		draw_rect(Rect2(at - Vector2(radius, radius), Vector2(radius, radius) * 2.0), Palette.BACKGROUND, false, 1.5)


## Whether any shown run has a character path of its own (a stance comparison).
func _own_paths() -> bool:
	for run: Dictionary in shown:
		if TakeData.has_own_player(run):
			return true
	return false


func _draw_player() -> void:
	var radius: float = _body_radius() * 1.1
	if not _own_paths():
		var at: Vector2 = to_screen(TakeData.position(data.player, tick))
		draw_circle(at, radius + 3.0, Palette.PLAYER_RING)
		draw_circle(at, radius, Palette.PLAYER)
		return
	# Each run's character, ringed in the run's colour; overlaid ones that stand together are one.
	var first: Vector2 = data.character_at(shown[0], tick)
	for i: int in range(shown.size()):
		var here: Vector2 = data.character_at(shown[i], tick)
		if i > 0 and here.distance_to(first) <= TOGETHER:
			continue
		var at: Vector2 = to_screen(here)
		draw_circle(at, radius + 3.5, colors[i])
		draw_circle(at, radius, Palette.PLAYER)


## A run's own walk: the trail so far, and each move it made (a line from where it was decided to
## where it ends, a marker there; bright from its decision to its arrival, dim after).
func _draw_moves(run: Dictionary, color: Color) -> void:
	if not TakeData.has_own_player(run):
		return
	var own: Dictionary = run["player"]
	var ticks: PackedInt32Array = own["t"]
	var points: PackedVector2Array = own["p"]
	var upto: int = TakeData.count_until(ticks, tick)
	if upto > 0:
		var trail: PackedVector2Array = PackedVector2Array()
		for k: int in range(upto):
			trail.append(to_screen(points[k]))
		trail.append(to_screen(data.character_at(run, tick)))
		draw_polyline(trail, Color(color, 0.35), 2.0)
	var moves: Array[Dictionary] = run["moves"]
	for step: Dictionary in moves:
		var t0: int = step["t0"]
		if t0 > tick:
			break
		var t1: int = step["t1"]
		var active: bool = tick <= t1
		var from: Vector2 = to_screen(step["from"])
		var to: Vector2 = to_screen(step["to"])
		var line: Color = Color(color, 0.9 if active else 0.4)
		var hop: bool = step["hop"]
		if hop:
			draw_dashed_line(from, to, line, 1.5, 6.0)
		else:
			draw_line(from, to, line, 1.5)
		draw_arc(to, 6.0, 0.0, TAU, 20, line, 2.0)
		draw_circle(to, 2.0, line)


func _body_radius() -> float:
	return clampf(5.0 * _zoom(), 3.5, 14.0)


## A run's casts in flight: the line from the caster to the focal point (dashed when the blades
## touched nothing), the focal ring, and each blade with a short trail.
func _draw_casts(run: Dictionary, color: Color) -> void:
	var casts: Array[Dictionary] = run["casts"]
	var cast_ticks: PackedInt32Array = run["cast_ticks"]
	var birth_lag: int = data.birth_lag
	var blade_life: int = data.blade_life
	var index: int = TakeData.count_until(cast_ticks, tick - blade_life)
	var blade_radius: float = clampf(2.6 * _zoom(), 2.5, 8.0)
	while index < casts.size():
		var found: Dictionary = casts[index]
		index += 1
		var birth: int = found["t"]
		if birth - birth_lag > tick:
			break
		var age: int = tick - birth
		var origin: Vector2 = found["o"]
		var focal: Vector2 = found["f"]
		var touched: int = found["n"]
		if TakeData.has_own_player(run):
			origin = data.character_at(run, birth - birth_lag)
		var from: Vector2 = to_screen(origin)
		var to: Vector2 = to_screen(focal)
		var fade: float = 1.0 if age < 0 else clampf(1.0 - float(age) / float(blade_life), 0.25, 1.0)
		var line: Color = Color(color, 0.75 * fade)
		if touched == 0:
			draw_dashed_line(from, to, line, 2.0, 8.0)
		else:
			draw_line(from, to, line, 2.0 if age >= 0 else 1.0)
		draw_arc(to, 7.0, 0.0, TAU, 20, Color(color, fade), 2.0)
		if age < 0:
			continue
		var blades: Array[PackedVector2Array] = found["b"]
		for blade: PackedVector2Array in blades:
			if age >= blade.size():
				continue
			var head: Vector2 = to_screen(blade[age])
			var tail: Vector2 = to_screen(blade[maxi(age - 3, 0)])
			draw_line(tail, head, Color(color, 0.55), blade_radius)
			draw_circle(head, blade_radius, color)
			draw_circle(head, blade_radius * 0.45, Palette.PLAYER)


func _draw_monsters() -> void:
	var radius: float = _body_radius()
	var bar: Vector2 = Vector2(clampf(22.0 * _zoom(), 18.0, 56.0), clampf(3.0 * _zoom(), 4.0, 7.0))
	var font: Font = get_theme_default_font()
	var view: Rect2 = Rect2(Vector2.ZERO, size).grow(40.0)
	var nearest: Dictionary = {}
	var nearest_gap: float = HOVER_PIXELS
	var monsters: Array[Dictionary] = data.monsters
	for monster: Dictionary in monsters:
		if not TakeData.seen(monster, tick):
			continue
		var at: Vector2 = to_screen(TakeData.position(monster, tick))
		if not view.has_point(at):
			continue
		var elite: bool = monster["elite"]
		var alive_somewhere: bool = false
		for i: int in range(shown.size()):
			var death: int = TakeData.death_in(shown[i], monster)
			if death < 0 or tick <= death:
				alive_somewhere = true
		var size_here: float = radius * (1.5 if elite else 1.0)
		if alive_somewhere:
			if elite:
				var diamond: PackedVector2Array = PackedVector2Array([
					at + Vector2(0, -size_here), at + Vector2(size_here, 0),
					at + Vector2(0, size_here), at + Vector2(-size_here, 0),
				])
				draw_colored_polygon(diamond, Palette.ELITE)
				diamond.append(diamond[0])
				draw_polyline(diamond, Palette.BACKGROUND, 1.5)
			else:
				draw_circle(at, size_here, Palette.MONSTER)
				draw_arc(at, size_here, 0.0, TAU, 16, Palette.BACKGROUND, 1.5)
		var top: float = at.y - size_here - 6.0 - bar.y * shown.size()
		for i: int in range(shown.size()):
			var run: Dictionary = shown[i]
			var death: int = TakeData.death_in(run, monster)
			var corner: Vector2 = Vector2(at.x - bar.x * 0.5, top + bar.y * i)
			if death >= 0 and tick > death:
				var corpse: Vector2 = to_screen(TakeData.position(monster, death))
				var shift: Vector2 = Vector2((i - (shown.size() - 1) * 0.5) * 6.0, 0)
				var fade: float = clampf(1.0 - float(tick - death) / float(FADE_TICKS), 0.3, 1.0)
				_draw_cross(corpse + shift, size_here, Color(colors[i], fade))
				continue
			var life: float = float(TakeData.life_in(run, monster, tick)) / 1000.0
			draw_rect(Rect2(corner, bar), Palette.BACKGROUND)
			draw_rect(Rect2(corner, Vector2(bar.x * life, bar.y)), colors[i])
			draw_rect(Rect2(corner, bar), Color(Palette.BACKGROUND, 0.9), false, 1.0)
		if alive_somewhere:
			var recorded_life: Dictionary = monster["recorded_life"]
			var life0: int = monster["life0"]
			var recorded: float = float(TakeData.step_at(recorded_life, tick, life0)) / 1000.0
			var under: Vector2 = Vector2(at.x - bar.x * 0.5, top + bar.y * shown.size() + 1.0)
			draw_rect(Rect2(under, Vector2(bar.x * recorded, 2.0)), Palette.TEXT_DIM)
		if _hover.x >= 0.0 and at.distance_to(_hover) < nearest_gap:
			nearest_gap = at.distance_to(_hover)
			nearest = monster
	if not nearest.is_empty():
		_draw_hover(nearest, font)


func _draw_cross(at: Vector2, radius: float, color: Color) -> void:
	var arm: Vector2 = Vector2(radius, radius) * 0.8
	draw_line(at - arm, at + arm, color, 3.0)
	draw_line(at + Vector2(-arm.x, arm.y), at + Vector2(arm.x, -arm.y), color, 3.0)


## What the monster under the pointer is: its name, full life, and its life in each run and as recorded.
func _draw_hover(monster: Dictionary, font: Font) -> void:
	var at: Vector2 = to_screen(TakeData.position(monster, tick))
	var name: String = monster["name"]
	var points: float = monster["points"]
	var elite: bool = monster["elite"]
	var lines: Array[String] = ["%s%s, %d life" % [name, " (elite)" if elite else "", int(points)]]
	var line_colors: Array[Color] = [Palette.TEXT]
	for i: int in range(shown.size()):
		var run: Dictionary = shown[i]
		var death: int = TakeData.death_in(run, monster)
		var run_name: String = run["name"]
		if death >= 0 and tick > death:
			lines.append("%s: dead %.1f s ago" % [run_name, float(tick - death) / data.rate])
		else:
			lines.append("%s: %d%%" % [run_name, roundi(float(TakeData.life_in(run, monster, tick)) / 10.0)])
		line_colors.append(colors[i])
	var recorded_life: Dictionary = monster["recorded_life"]
	var life0: int = monster["life0"]
	lines.append("in the game: %d%%" % roundi(float(TakeData.step_at(recorded_life, tick, life0)) / 10.0))
	line_colors.append(Palette.TEXT_DIM)
	var font_size: int = 17
	var width: float = 0.0
	for text: String in lines:
		width = maxf(width, font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x)
	var line_height: float = font.get_height(font_size)
	var box: Rect2 = Rect2(at + Vector2(18, 10), Vector2(width + 16.0, line_height * lines.size() + 10.0))
	box.position.x = minf(box.position.x, size.x - box.size.x - 4.0)
	box.position.y = minf(box.position.y, size.y - box.size.y - 4.0)
	draw_rect(box, Color(Palette.PANEL, 0.95))
	draw_rect(box, Palette.PANEL_EDGE, false, 1.0)
	for i: int in range(lines.size()):
		var baseline: Vector2 = box.position + Vector2(8.0, 5.0 + font.get_ascent(font_size) + line_height * i)
		draw_string(font, baseline, lines[i], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, line_colors[i])


## Which run this view shows, in the run's colour, top left.
func _draw_titles() -> void:
	var font: Font = get_theme_default_font()
	var font_size: int = 20
	var line_height: float = font.get_height(font_size)
	var widest: float = 0.0
	var texts: Array[String] = []
	for i: int in range(shown.size()):
		var run: Dictionary = shown[i]
		var policy: bool = run["policy"]
		var run_name: String = run["name"]
		var label: String = run["label"]
		var text: String = "POLICY: %s" % run_name
		if not policy:
			text = label if not label.is_empty() else "RECORDED: the player's casts"
		texts.append(text)
		widest = maxf(widest, font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x)
	var box: Rect2 = Rect2(Vector2(8, 8), Vector2(widest + 44.0, line_height * texts.size() + 10.0))
	draw_rect(box, Color(Palette.PANEL, 0.9))
	for i: int in range(texts.size()):
		var row: float = box.position.y + 5.0 + line_height * i
		draw_rect(Rect2(Vector2(box.position.x + 8.0, row + 4.0), Vector2(18, line_height - 8.0)), colors[i])
		var baseline: Vector2 = Vector2(box.position.x + 34.0, row + font.get_ascent(font_size))
		draw_string(font, baseline, texts[i], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, colors[i])
