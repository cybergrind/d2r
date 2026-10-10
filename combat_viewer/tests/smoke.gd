extends SceneTree
## A headless check of the decoder and of the scene: load one exported take, read every track,
## series and blade the views read, step the main scene through it, and print a summary.
## `godot --headless --path combat_viewer --script res://tests/smoke.gd -- <take.json>`; exits 1 on a problem.

const TakeData := preload("res://take_data.gd")


func _init() -> void:
	var arguments: PackedStringArray = OS.get_cmdline_user_args()
	if arguments.is_empty():
		print("usage: -- <take.json>")
		quit(2)
		return
	var data: RefCounted = TakeData.load_file(arguments[0])
	if not data.problem.is_empty():
		print("problem: ", data.problem)
		quit(1)
		return
	var problems: PackedStringArray = PackedStringArray()
	var blades: int = 0
	var longest: int = 0
	for run: Dictionary in data.runs:
		var casts: Array[Dictionary] = run["casts"]
		for found: Dictionary in casts:
			var paths: Array[PackedVector2Array] = found["b"]
			if paths.size() != 5:
				problems.append("%s: a cast at %d with %d blades" % [run["name"], found["t"], paths.size()])
			for path: PackedVector2Array in paths:
				blades += 1
				longest = maxi(longest, path.size())
				if path.is_empty() or path.size() > data.blade_life:
					problems.append("%s: a blade of %d positions" % [run["name"], path.size()])
		var end_totals: Dictionary = data.totals(run, data.end)
		var score: Dictionary = run["score"]
		if end_totals["kills"] != int(score.get("kills", -1)) or end_totals["casts"] != int(score.get("casts", -1)):
			problems.append("%s: totals at the end %s against the score %s" % [run["name"], end_totals, score])
		if absi(end_totals["taken"] - int(score.get("life_taken", -1))) > 1:
			problems.append("%s: life taken %d against %s" % [run["name"], end_totals["taken"], score.get("life_taken")])
		print("%-9s casts %4d  kills %4d  life taken %9d  gain %s" % [
			run["name"], end_totals["casts"], end_totals["kills"], end_totals["taken"], str(score.get("gain"))
		])
	var seen_ticks: int = 0
	var middle: int = (data.start + data.end) / 2
	for monster: Dictionary in data.monsters:
		if TakeData.seen(monster, middle):
			seen_ticks += 1
			var at: Vector2 = TakeData.position(monster, middle)
			if not data.bounds.grow(1.0).has_point(at):
				problems.append("monster %s outside the bounds at tick %d: %s" % [monster["key"], middle, at])
		for run: Dictionary in data.runs:
			var life: int = TakeData.life_in(run, monster, data.end)
			var death: int = TakeData.death_in(run, monster)
			if (death >= 0) != (life == 0):
				problems.append("%s: monster %s has life %d and death %d" % [run["name"], monster["key"], life, death])
	if not data.bounds.grow(1.0).has_point(TakeData.position(data.player, middle)):
		problems.append("the player outside the bounds")
	print("%s: ticks %d-%d, %d monsters (%d at tick %d), %d companions, %d doors, walls %s, %d blades (longest %d)" % [
		data.take, data.start, data.end, data.monsters.size(), seen_ticks, middle, data.companions.size(),
		data.doors.size(), "none" if data.wall_texture == null else str(data.wall_rect.size), blades, longest
	])
	for name: String in data.policy_names():
		print("moments for %s: %d" % [name, data.moments_of(name).size()])
	for problem: String in problems:
		print("PROBLEM ", problem)
	quit(1 if not problems.is_empty() else 0)
