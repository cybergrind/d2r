extends RefCounted
## One exported take (README.md, "The exported file"), decoded for drawing.
##
## Positions become world units from the file's origin (file units / scale). A track becomes
## {"seen": PackedInt32Array (flat first, last pairs), "t": PackedInt32Array (keyframe ticks),
## "p": PackedVector2Array (keyframe positions)}; a step series becomes {"t": PackedInt32Array,
## "v": PackedInt32Array}. Blades are unpacked to one position per tick.

const Palette := preload("res://palette.gd")

var problem: String = ""  # why the file could not be used; empty when it could
var path: String = ""
var take: String = ""
var area_name: String = ""
var start: int = 0
var end: int = 0
var rate: float = 25.0
var seconds: float = 0.0
var birth_lag: int = 5
var blade_life: int = 38
var contact_radius: float = 2.0
var bounds: Rect2 = Rect2()
var player: Dictionary = {}
var player_run: PackedInt32Array = PackedInt32Array()
var pointer: Dictionary = {}
var monsters: Array[Dictionary] = []
var companions: Array[Dictionary] = []
var doors: Array[Dictionary] = []
var wall_texture: ImageTexture = null
var wall_rect: Rect2 = Rect2()
var recorded_taken: Dictionary = {}
var recorded_kills: PackedInt32Array = PackedInt32Array()
var gate: Dictionary = {}
var runs: Array[Dictionary] = []  # runs[0] is the recorded one
var moments: Dictionary = {}  # policy name -> Array of moments


## The take in the file at `file_path`; `problem` says why when it could not be read.
static func load_file(file_path: String) -> RefCounted:
	var data: RefCounted = new()
	data.path = file_path
	var text: String = FileAccess.get_file_as_string(file_path)
	if text.is_empty():
		data.problem = "Could not read %s" % file_path
		return data
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		data.problem = "%s is not a take exported by inventory_tracking.combat.viz" % file_path
		return data
	var raw: Dictionary = parsed
	if int(raw.get("schema", 0)) != 1 or not raw.has("runs"):
		data.problem = "%s has schema %s; this viewer reads schema 1" % [file_path, str(raw.get("schema"))]
		return data
	data._decode(raw)
	return data


func _decode(raw: Dictionary) -> void:
	take = str(raw.get("take", "?"))
	area_name = str(raw.get("area_name", ""))
	start = int(raw.get("start", 0))
	end = int(raw.get("end", start))
	rate = float(raw.get("rate", 25.0))
	seconds = float(raw.get("seconds", 0.0))
	birth_lag = int(raw.get("birth_lag", 5))
	blade_life = int(raw.get("blade_life", 38))
	var scale: float = float(raw.get("scale", 10))
	contact_radius = float(raw.get("contact_radius", 20)) / scale
	var box: Array = raw.get("bounds", [0, 0, 0, 0])
	bounds = Rect2(
		float(box[0]) / scale, float(box[1]) / scale,
		(float(box[2]) - float(box[0])) / scale, (float(box[3]) - float(box[1])) / scale
	)
	var raw_player: Dictionary = raw.get("player", {})
	player = _track(raw_player, scale)
	player_run = _spans(raw_player.get("run", []))
	pointer = _track(raw.get("pointer", {}), scale)
	monsters.clear()
	var raw_monsters: Array = raw.get("monsters", [])
	for item: Variant in raw_monsters:
		var found: Dictionary = item
		var recorded: Dictionary = found.get("recorded", {})
		var death: Variant = recorded.get("death")
		var monster: Dictionary = _track(found, scale)
		monster["unit"] = int(found.get("unit", 0))
		monster["key"] = str(int(found.get("unit", 0)))
		monster["txt"] = int(found.get("txt", 0))
		monster["name"] = str(found.get("name", ""))
		monster["elite"] = bool(found.get("elite", false))
		monster["points"] = float(found.get("points", 0))
		monster["life0"] = int(found.get("life0", 1000))
		monster["recorded_death"] = -1 if death == null else int(death)
		monster["recorded_life"] = _steps(recorded.get("life", []))
		monsters.append(monster)
		if death != null:
			recorded_kills.append(int(death))
	recorded_kills.sort()
	companions.clear()
	var raw_companions: Array = raw.get("companions", [])
	for item: Variant in raw_companions:
		var found: Dictionary = item
		var companion: Dictionary = _track(found, scale)
		companion["name"] = str(found.get("name", ""))
		companions.append(companion)
	doors.clear()
	var raw_doors: Array = raw.get("doors", [])
	for item: Variant in raw_doors:
		var found: Dictionary = item
		doors.append({
			"at": Vector2(float(found.get("x", 0)), float(found.get("y", 0))) / scale,
			"r": float(found.get("r", 10)) / scale,
			"seen": _spans(found.get("seen", [])),
			"closed": _spans(found.get("closed", [])),
		})
	_decode_walls(raw.get("walls"), scale)
	var raw_recorded: Dictionary = raw.get("recorded", {})
	recorded_taken = _steps(raw_recorded.get("taken", []))
	gate = raw.get("gate", {})
	runs.clear()
	var raw_runs: Array = raw.get("runs", [])
	for item: Variant in raw_runs:
		var found: Dictionary = item
		runs.append(_run(found, scale))
	moments = raw.get("moments", {})
	if runs.is_empty():
		problem = "%s holds no runs" % path


func _track(raw: Dictionary, scale: float) -> Dictionary:
	var keys: Array = raw.get("k", [])
	var ticks: PackedInt32Array = PackedInt32Array()
	var points: PackedVector2Array = PackedVector2Array()
	var count: int = keys.size() / 3
	ticks.resize(count)
	points.resize(count)
	for i: int in range(count):
		ticks[i] = int(keys[i * 3])
		points[i] = Vector2(float(keys[i * 3 + 1]), float(keys[i * 3 + 2])) / scale
	return {"seen": _spans(raw.get("seen", [])), "t": ticks, "p": points}


func _spans(raw: Variant) -> PackedInt32Array:
	var out: PackedInt32Array = PackedInt32Array()
	if typeof(raw) != TYPE_ARRAY:
		return out
	var found: Array = raw
	for item: Variant in found:
		var span: Array = item
		out.append(int(span[0]))
		out.append(int(span[1]))
	return out


func _steps(raw: Variant) -> Dictionary:
	var ticks: PackedInt32Array = PackedInt32Array()
	var values: PackedInt32Array = PackedInt32Array()
	if typeof(raw) == TYPE_ARRAY:
		var found: Array = raw
		var count: int = found.size() / 2
		ticks.resize(count)
		values.resize(count)
		for i: int in range(count):
			ticks[i] = int(found[i * 2])
			values[i] = int(found[i * 2 + 1])
	return {"t": ticks, "v": values}


func _decode_walls(raw: Variant, scale: float) -> void:
	wall_texture = null
	if typeof(raw) != TYPE_DICTIONARY:
		return
	var found: Dictionary = raw
	var width: int = int(found.get("w", 0))
	var height: int = int(found.get("h", 0))
	if width <= 0 or height <= 0:
		return
	var packed: PackedByteArray = Marshalls.base64_to_raw(str(found.get("cells", "")))
	var cells: PackedByteArray = packed.decompress(width * height, FileAccess.COMPRESSION_DEFLATE)
	if cells.size() != width * height:
		return
	var colors: Array[Color] = [Palette.UNREAD, Palette.FLOOR, Palette.LOW, Palette.WALL]
	var pixels: PackedByteArray = PackedByteArray()
	pixels.resize(width * height * 4)
	for i: int in range(width * height):
		var color: Color = colors[mini(cells[i], 3)]
		pixels[i * 4] = color.r8
		pixels[i * 4 + 1] = color.g8
		pixels[i * 4 + 2] = color.b8
		pixels[i * 4 + 3] = 0 if cells[i] == 0 else 255
	var image: Image = Image.create_from_data(width, height, false, Image.FORMAT_RGBA8, pixels)
	wall_texture = ImageTexture.create_from_image(image)
	wall_rect = Rect2(float(found.get("x", 0)) / scale, float(found.get("y", 0)) / scale, width, height)


func _run(raw: Dictionary, scale: float) -> Dictionary:
	var casts: Array[Dictionary] = []
	var cast_ticks: PackedInt32Array = PackedInt32Array()
	var raw_casts: Array = raw.get("casts", [])
	for item: Variant in raw_casts:
		var found: Dictionary = item
		var origin: Array = found.get("o", [0, 0])
		var focal: Array = found.get("f", [0, 0])
		var blades: Array[PackedVector2Array] = []
		var raw_blades: Array = found.get("b", [])
		for blade: Variant in raw_blades:
			blades.append(_blade(blade, scale))
		var tick: int = int(found.get("t", 0))
		casts.append({
			"t": tick,
			"o": Vector2(float(origin[0]), float(origin[1])) / scale,
			"f": Vector2(float(focal[0]), float(focal[1])) / scale,
			"n": int(found.get("n", 0)),
			"b": blades,
		})
		cast_ticks.append(tick)
	var life: Dictionary = {}
	var raw_life: Dictionary = raw.get("life", {})
	for unit: Variant in raw_life:
		life[str(unit)] = _steps(raw_life[unit])
	var deaths: Dictionary = {}
	var death_ticks: PackedInt32Array = PackedInt32Array()
	var raw_deaths: Dictionary = raw.get("deaths", {})
	for unit: Variant in raw_deaths:
		deaths[str(unit)] = int(raw_deaths[unit])
		death_ticks.append(int(raw_deaths[unit]))
	death_ticks.sort()
	return {
		"name": str(raw.get("name", "?")),
		"label": str(raw.get("label", "")),
		"policy": bool(raw.get("policy", false)),
		"score": raw.get("score", {}),
		"casts": casts,
		"cast_ticks": cast_ticks,
		"life": life,
		"deaths": deaths,
		"death_ticks": death_ticks,
		"taken": _steps(raw.get("taken", [])),
	}


## A packed blade [x0, y0, x1, y1, n, dx, dy, ...] as its position at each tick from the cast's.
func _blade(raw: Variant, scale: float) -> PackedVector2Array:
	var out: PackedVector2Array = PackedVector2Array()
	var found: Array = raw
	if found.size() < 5:
		return out
	var from: Vector2 = Vector2(float(found[0]), float(found[1]))
	var to: Vector2 = Vector2(float(found[2]), float(found[3]))
	var steps: int = int(found[4])
	for k: int in range(steps + 1):
		out.append(from.lerp(to, float(k) / float(steps) if steps > 0 else 0.0) / scale)
	var at: Vector2 = to
	var index: int = 5
	while index + 1 < found.size():
		at += Vector2(float(found[index]), float(found[index + 1]))
		out.append(at / scale)
		index += 2
	return out


## Whether `tick` lies inside one of the flat [first, last, ...] spans.
static func in_spans(spans: PackedInt32Array, tick: int) -> bool:
	var low: int = 0
	var high: int = spans.size() / 2 - 1
	while low <= high:
		var middle: int = (low + high) / 2
		if tick < spans[middle * 2]:
			high = middle - 1
		elif tick > spans[middle * 2 + 1]:
			low = middle + 1
		else:
			return true
	return false


## Whether a track's thing is there at `tick`.
static func seen(track: Dictionary, tick: int) -> bool:
	var spans: PackedInt32Array = track["seen"]
	return in_spans(spans, tick)


## Where a track's thing stands at `tick`: its last keyframe at or before it (its first one before that).
static func position(track: Dictionary, tick: int) -> Vector2:
	var ticks: PackedInt32Array = track["t"]
	var points: PackedVector2Array = track["p"]
	if points.is_empty():
		return Vector2.ZERO
	var index: int = ticks.bsearch(tick, false) - 1
	return points[clampi(index, 0, points.size() - 1)]


## The last tick a track's thing was seen at, or -1.
static func last_seen(track: Dictionary) -> int:
	var spans: PackedInt32Array = track["seen"]
	return -1 if spans.is_empty() else spans[spans.size() - 1]


## A step series' value at `tick`, or `before` ahead of its first entry.
static func step_at(series: Dictionary, tick: int, before: int) -> int:
	var ticks: PackedInt32Array = series["t"]
	var values: PackedInt32Array = series["v"]
	var index: int = ticks.bsearch(tick, false) - 1
	return before if index < 0 else values[index]


## How many of the ascending `ticks` are at or before `tick`.
static func count_until(ticks: PackedInt32Array, tick: int) -> int:
	return ticks.bsearch(tick, false)


## A monster's life in a run at `tick`, in thousandths of its full life.
static func life_in(run: Dictionary, monster: Dictionary, tick: int) -> int:
	var life: Dictionary = run["life"]
	var key: String = monster["key"]
	var before: int = monster["life0"]
	if not life.has(key):
		return before
	var series: Dictionary = life[key]
	return step_at(series, tick, before)


## The tick a monster died at in a run, or -1 when the run did not kill it.
static func death_in(run: Dictionary, monster: Dictionary) -> int:
	var deaths: Dictionary = run["deaths"]
	var key: String = monster["key"]
	if not deaths.has(key):
		return -1
	var tick: int = deaths[key]
	return tick


## The running totals of a run at `tick`: life taken, kills and casts so far.
func totals(run: Dictionary, tick: int) -> Dictionary:
	var taken: Dictionary = run["taken"]
	var death_ticks: PackedInt32Array = run["death_ticks"]
	var cast_ticks: PackedInt32Array = run["cast_ticks"]
	return {
		"taken": step_at(taken, tick, 0),
		"kills": count_until(death_ticks, tick),
		"casts": count_until(cast_ticks, tick),
	}


## The run called `name`, or the first policy run, or the recorded one.
func run_named(name: String) -> Dictionary:
	for run: Dictionary in runs:
		if run["name"] == name:
			return run
	return runs[mini(1, runs.size() - 1)]


## The names of the policy runs, in the file's order.
func policy_names() -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()
	for run: Dictionary in runs:
		if run["policy"]:
			out.append(str(run["name"]))
	return out


## The moments of a policy, as an Array of Dictionaries (first, last, kind, label, value).
func moments_of(name: String) -> Array:
	var found: Variant = moments.get(name, [])
	if typeof(found) != TYPE_ARRAY:
		return []
	return found
