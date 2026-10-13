extends Node
## Exports takes for the viewer by running the exporter (`python -m inventory_tracking.builds.warlock.echoing_strike.viz
## <take>`, through uv, in the repository) one take at a time, off the main thread, and passes on the
## stages it prints (`[2/6] the recorded casts`). The exporter refreshes index.json itself; whoever
## hears `finished` reads it again.

signal progressed(take: String, done: int, total: int, stage: String)
signal finished(take: String, ok: bool, message: String)  ## message: the exporter's last line

const PROGRAM := "uv"
const MODULE := "inventory_tracking.builds.warlock.echoing_strike.viz"
## The situations' exporter (tests/.../arena/situations/export_viz.py): asked like MODULE for one situation,
## with `--list` for the catalog, and with `--tasks <take>` for a take's task sidecar.
const SITUATIONS := "tests.inventory_tracking.scenarios.arena.situations.export_viz"

var module: String = MODULE  # the exporter the next requests run

var _queue: Array[Dictionary] = []
var _thread: Thread = null
var _current: String = ""
var _current_tasks: bool = false  # the job running is a take's task sidecar: its failure is not the take's
var _pid: int = -1


## Queue the take in `take_directory` for export to `out`; nothing when it is already waiting or running.
func request(take_directory: String, out: String, policies: PackedStringArray) -> void:
	var take: String = take_directory.get_file()
	if is_pending(take):
		return
	_queue.append({"take": take, "source": take_directory, "out": out, "policies": policies, "module": module})
	if module == MODULE:
		# After a take's own export: its task sidecar (what the macro was doing), from the take's events.
		_queue.append({"take": take, "source": take_directory, "out": out, "policies": PackedStringArray(), "module": SITUATIONS, "tasks": true})
	_start_next()


## The situations' catalog written into `out`/index.json, at once (a second or two); "" or what went wrong.
func list_situations(out: String) -> String:
	var said: Array = []
	var code: int = OS.execute(PROGRAM, PackedStringArray([
		"--directory", _repository(), "run", "--offline", "python", "-m", SITUATIONS, "--list", "--out", out,
	]), said, true)
	if code == 0:
		return ""
	var lines: PackedStringArray = "".join(PackedStringArray(said)).strip_edges().split("\n")
	return lines[-1]


func is_pending(take: String) -> bool:
	if take == _current:
		return true
	for job: Dictionary in _queue:
		if job["take"] == take:
			return true
	return false


func _start_next() -> void:
	if _thread != null or _queue.is_empty():
		return
	var job: Dictionary = _queue.pop_front()
	_current = job["take"]
	_current_tasks = job.get("tasks", false)
	_thread = Thread.new()
	_thread.start(_work.bind(job))


## The repository: the exporter is run there (the viewer's project is a directory of it).
func _repository() -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").simplify_path()


func _arguments(job: Dictionary) -> PackedStringArray:
	if job.get("tasks", false):
		return PackedStringArray([
			"--directory", _repository(), "run", "--offline", "python", "-m", SITUATIONS, "--tasks", job["source"], "--out", job["out"],
		])
	var arguments: PackedStringArray = PackedStringArray([
		"--directory", _repository(), "run", "--offline", "python", "-m", job.get("module", MODULE), job["source"], "--out", job["out"],
	])
	var policies: PackedStringArray = job["policies"]
	if not policies.is_empty():
		arguments.append("--policies")
		arguments.append(",".join(policies))
	return arguments


## In the thread: run the exporter, pass each line on, then report how it ended.
func _work(job: Dictionary) -> void:
	var take: String = job["take"]
	var process: Dictionary = OS.execute_with_pipe(PROGRAM, _arguments(job))
	if process.is_empty():
		_ended.call_deferred(take, false, "could not start %s" % PROGRAM)
		return
	_pid = process["pid"]
	var output: FileAccess = process["stdio"]
	var errors: FileAccess = process["stderr"]
	var last: String = ""
	while output.is_open() and output.get_error() == OK:
		var line: String = output.get_line().strip_edges()
		if line.is_empty():
			continue
		last = line
		_heard.call_deferred(take, line)
	while OS.is_process_running(_pid):
		OS.delay_msec(20)
	var ok: bool = OS.get_process_exit_code(_pid) == 0
	if not ok:
		# A traceback ends with the error; a take with too few casts says so on the output.
		var said: PackedStringArray = errors.get_as_text().strip_edges().split("\n")
		if not said[-1].is_empty():
			last = said[-1].strip_edges()
	_ended.call_deferred(take, ok, last)


func _heard(take: String, line: String) -> void:
	if not line.begins_with("["):
		return
	var close: int = line.find("]")
	var counts: PackedStringArray = line.substr(1, close - 1).split("/")
	if close < 0 or counts.size() != 2:
		return
	progressed.emit(take, int(counts[0]), int(counts[1]), line.substr(close + 1).strip_edges())


func _ended(take: String, ok: bool, message: String) -> void:
	if _thread == null:
		return
	_thread.wait_to_finish()
	_thread = null
	_current = ""
	_pid = -1
	if _current_tasks:
		ok = true  # no sidecar: the take plays without a task readout
		message = ""
	else:
		if not ok:  # the take has no file: no sidecar either, and its failure stays on its row
			_queue = _queue.filter(func(job: Dictionary) -> bool: return not (job["take"] == take and job.get("tasks", false)))
	finished.emit(take, ok, message)
	_start_next()


func _exit_tree() -> void:
	_queue.clear()
	if _thread == null:
		return
	if _pid > 0:
		OS.kill(_pid)
	_thread.wait_to_finish()
	_thread = null
