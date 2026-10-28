# Focused checks

Latest recorded source gate: **262 checks including deferred host persistence (2026-10-28)**.
See [the repeat Ponytail audit](../docs/PONYTAIL_REAUDIT_2026-10-23.md) for the latest
baseline, per-change checks and native gates; [the earlier refactor audit](../docs/REFACTOR_AUDIT.md)
records the preceding pass. Counts in the
individual correction records below belong to those historical source stages. Current test
output is authoritative for any later checkout. Device evidence and remaining acceptance
cases are in the API audit and `runtime/README.md`; source checks do not replace those gates.

Non-build checks (Python 3 and pycparser):

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'

Host persistence (2026-10-28): Main selection connects discovered/saved value copies without
writing the host store. The API updates connection metadata only for authenticated paired
hosts; new discovered/manual hosts stay temporary until PIN/HTTPS success. Pairing success
creates the record before resolving/writing `server.pem`; metadata/path/assignment/pin-write
failures remain separately logged protocol successes. LiveArea waits for paired state and
captures the newly saved UUID on pairing completion. These serial source checks do not prove
real crypto, PAF/thread ownership, Vita storage durability or restart behavior.

`test_page_navigation.py` interprets the actual Apps animation helper, state,
completion, input admission and destructor cleanup with serial PAF timer/widget
mocks. It covers both completion orders, list readiness before/after entrance,
PIN mid-stack activation, Back/busy gating, allocation and native API failures,
forced-close callback cancellation, Main restoration and CXML pivot/list bounds.
The Apps title must share the animated content container; this resource assertion
reproduces the 2026-10-28 late-return overlap before the CXML correction.
`test_livearea_launch.py` also rejects LiveArea admission during transitions.
These are non-build source checks; native ownership/ABI, interpolation,
projection/clipping, focus/scroll retention and Vita appearance remain unverified.
See [UI guide §5.6](../docs/UI.md#56-photos-folded-parent-navigation--2026-10-28).

`test_motion.py` interprets the actual gyro/accelerometer worker loops, stop and host-rate
callback with serial atomics/send/delay mocks. Host rate 0, stop and a changed positive rate
are injected during sending: the current delay must use its validated snapshot, and the next
iteration must observe the update. The old source raises division-by-zero in four subcases
and changes the current interval in two more. Inactive/disabled/zero-rate workers stay idle.
Only unused argument casts are removed for parsing. This does not execute threads, native
atomics, sensors, the Vita ABI or real Moonlight transport; build/device checks remain separate.
Two further checks interpret actual sensor send bodies: asymmetric raw samples must retain
SDL x/y/z order and convert rad/s to deg/s and g to m/s²; a failed read must send nothing.
The old common `28.0f` scale fails both unit cases. Raw samples and errors are mocked.
Unit/axis references are the vendored `Limelight.h` motion contract and the
[upstream SDL Vita sensor driver](https://github.com/libsdl-org/SDL/blob/main/src/sensor/vita/SDL_vitasensor.c),
whose gyro uses SDL's [radians/second convention](https://wiki.libsdl.org/SDL3/SDL_SensorType).
Two overlay checks interpret the shared suspended flag and the actual input-process prefix:
system UI pauses both workers, host rate changes are retained while paused, and foreground
return resumes the requested rates. Motion starts suspended until the input loop applies
its overlay state. This follows the existing cached AppMgr input policy, including its
unknown-state behavior; it is not independent proof of native overlay/suspend timing.
The setup retry check interprets init/start: sampling or either worker setup failure must
leave motion inactive/uninitialized; the next start retries missing setup, accepting already
active sampling and retaining successful workers. Disable/re-enable reuses the completed
setup and clears rates. Old code fails all three injected failures. Worker creation itself
is mocked by its started-flag contract; no real creation/cleanup or device recovery is tested.

`test_ui_resources.py` also checks that native Settings' `Licenses and credits`
section is read-only, all its labels resolve, and the component credits, original
mDNS permission, OpenSSL acknowledgments and source-download address remain
present. The check fails before adding the section. It does not compile the RCO
or establish native text wrapping/scrolling, navigation or licensing completeness.

`test_settings_behavior.py` interprets the actual video-options setter before common-c's
callback snapshot, covering RFI enabled on the first connection and repeated On/Off changes.
The old source fails the enabled snapshots. Decoder setup must no longer mutate the original
callbacks too late. No decoder, common-c runtime, compilation or packet-recovery test is run.
Two keyboard checks interpret the actual in-stream text sender using native PAF conversion
and UTF-8 transport mocks. ASCII punctuation/case, Cyrillic, French/German/Spanish accents
and a surrogate pair must produce one complete UTF-8 payload with its byte length. Null/empty
input, conversion failure and negative/positive queue errors never fall back to VK events.
The old ASCII/keycode loop fails all language payload cases. String methods/casts are adapted
for interpretation; real PAF UTF conversion, IME, host delivery and C++/ABI are not executed.
The special-key check interprets the actual touch-zone block: top-right requests stop with
PS capture On or Off and returns before further input, holding does not repeat, and release
rearms the zone. Other corners and disabled/DS4/mouse/tablet modes retain their behavior.
Touch samples and stream stop are mocked; native polling, threads and teardown are not run.

`test_livearea.py` interprets the actual frame builder and `LiveAreaService` with
serial native API mocks: bounded XML/UTF-8 escaping, owned names, first-six cache
capture, shorter/empty lists, host changes, one pending request, coalescing (also
after an older failure), module/submission/completion errors and shutdown.
The installation-default check requires native welcome strings, rejects sample
app/PC labels, images/backgrounds and targets in the packaged template, and
checks packaged asset entries, indexed PNG dimensions and palette alpha, including
the gate's `startup.png`. Dynamic
checks cover welcome → Apps → empty transitions, row/card geometry, icon presence,
left alignment/icon spacing and removal of stale backdrops/targets from unused
slots. Resource checks resolve CMake source/destination entries, including the
app marker packaged directly from `icon0.png`.
The optional Browser importer checks exact RGBA equality during conversion;
this is source-asset validation, not resource compilation or device rendering.
`test_event_queue.py` checks capture after worker completion and before page
callbacks, plus submission gating while busy/streaming/paused. No native code,
module, shell/database, filesystem write or Vita call is executed. Build/ABI,
PAF responsiveness, display and persistence remain maintainer validation; see
[the LiveArea device procedure](../docs/LIVEAREA.md).

Launch follow-up adds target round trips, version/hex/decimal/overflow rejection,
and inactive empty/UUID-less slots. `test_livearea_launch.py` interprets the
actual saved-UUID resolver (including duplicate names/deleted identity), Main
admission, fresh-ID one-shot selection and AppMgr/AppUtil poll with serial
state/event/error mocks. It checks type 0/non-LiveArea events are not parsed,
100 ms polling, API failure/overlay/busy/stale rejection and PC/app routing.
The consuming-queue check advances across multiple polling deadlines: a launch event waits
while system UI overlays the app, is consumed once after resume, and a tap rejected while
busy is not replayed after admission reopens. A separate check fills all 1019 parameter
bytes without a terminator (leaving the reserved tail zero) and requires rejection before
the string parser or connection. These use the actual polling body with serial API mocks.
Main → PIN → Apps constructor arguments and pending-intent error clears are
source-inspected. The SDK output layout is asserted in the binding; no test
executes the native parser, compilation, page animation, real cancellation,
networking or cold/resumed Vita launch delivery.

`test_ci_setup.py` executes only the standalone checksum/OpenSSL-pin helper definitions,
never the setup script's main body or build commands. It checks valid/corrupt/missing archive
bytes (including paths with spaces), explicit full-commit replacement, invalid commits,
missing/changed/duplicate source recipes, and failure stopping before the next step without
rewriting a rejected recipe. These do not validate a real dependency or application build.
Static workflow validation uses `actionlint`; `bash -n scripts/ci_setup.sh` checks shell syntax.

`test_build_profiles.py` executes only extracted argument-parser definitions,
checking the system default and explicit normal/system selection. It never runs
the build script's main body or any compiler/resource/packaging command.
`test_release.py` uses synthetic ZIP/SFO fixtures and mocked GitHub calls to
check Vita version/tag validation, stable-version ordering, canonical tag pushes
and exact remote tag-to-built-commit binding (lightweight and annotated),
real-404 handling, VPK identity/profile/INI rejection, exact hashes, versioned
payload URLs, CDATA changeinfo, complete asset sets, draft/upload/publish order,
upload failure and a tag moved during upload. Tag refs are never changed.
It performs no real application packaging, network request, Git ref/release change
or publication. The workflow also passes `actionlint`; a maintainer-run clean
build, actual publication and Vita HomebrewUpdate acceptance remain separate gates.

`test_stream_warnings.py` adds five non-build checks interpreting the actual warning policy,
receive-counter/status functions and PAF badge state transitions. They cover healthy low-bitrate
scenes, loss/bitrate/stall/startup boundaries, receive metrics without detailed statistics,
stale/inactive generations, reconnect reset, stop/cancel guards, warning changes, three-second
recovery hold and immediate stop hiding. Resource labels and polling wiring are source-checked.
Clock, bucket advancement, mutexes, memory clearing and PAF are serial mocks; detailed decoder/GPU
timing, native ABI, real packet recovery/concurrency, RCO layout and Vita behavior are unverified.

`test_debug_settings.py` adds four checks interpreting actual startup/callback bodies:
AppSettings before host initialization and error propagation; toggling both ways while stored
values are stale; missing callback arguments/other settings; and closure applying saved runtime
values before the memory diagnostic/event. The old source fails ten subcases. AppSettings,
logging and initialization are serial mocks; native callback timing, persistence, plugin loading,
compilation and Vita cold-start/switch behavior remain maintainer validation.

Main background discovery replaces the former Search-specific lifecycle/list checks.
`test_discovery_lifecycle.py` interprets the actual persistent worker, activation/stop, generation
acceptance, locked value publication and aging with serial clock/kernel/socket mocks. It checks
five-second completion-to-send deadlines (including simulated send latency), one worker across
renewals/restarts, no catch-up, cancellation/stale observations, unchanged/value-copied snapshots,
expiry refresh, error-frozen age/log deduplication, lease timeout and final cleanup. Connect's
worker barrier and UI idle-poll wiring are also inspected.
The pause-crash follow-up changes worker control mocks to require pthread creation before
cancellable condition waiting, checks 64 KiB attributes and init/stack/create failure cleanup,
retry and final join, and interprets the Connect job's worker-only idle polling without pthread
condition waits on foreign PAF threads. The supplied core/local ELF establish the native failure
separately (UI guide); the serial model cannot reproduce Vita pthread TLS/ABI itself.
`test_host_lists.py` interprets actual Main eligibility, saved/discovered merging, identity,
row-state/token preparation, incremental cell-edit planner, deletion and selection without saving.
It covers >8 rows, equal names, stronger conflicting identity/custom ports,
retained tokens/selection, stale replaced tokens, temporary-to-saved, failed reads, discovery
growth and no edits for unchanged rows. The linker follow-up also interprets the actual
PAF token-buffer mutation branches (front/middle/end insertion/deletion, move, singleton/empty)
and rejects reintroducing `std::vector` or sized PAF scratch constructors. These serial array
checks do not verify native allocation or successful linking. Two checkbox regressions interpret
actual row/Select All toggles, live-item updates and focus capture with token-only child lookup
after widget renaming, including 12 PCs and missing/recreated virtualized items. They reproduced
the old missing-checkmark/focus lookups and pass after correction; native PAF rendering and
input remain maintainer validation. XML checks compare saved/temporary columns and require
no temporary dot/Search resource. Return-to-Main routes and real installed PAF declarations are
source-inspected. `test_event_queue.py` also executes discovery snapshot coalescing and rejection
of stale/hidden-page delivery before subsequent connection events.
These mocks do not execute C++/CXML, real pthread/mutex scheduling, native PAF focus/scroll,
AppMgr suspension, sockets or Vita timing. Build/RCO and device acceptance remain pending.

The PC availability trial adds six checks in `test_host_availability.py` and one
in `test_event_queue.py`: actual TCP probe control flow with mocked native API
results/cleanup, cancellation and timeout; DNS handling; exact 30-second expiry and
UUID/address/port matching; failed submission preserving the previous drain barrier;
foreground-worker/shutdown ordering; availability snapshot coalescing and main-thread
delivery. The follow-up extends actual-predicate checks to the 15-second repeat
boundary, unfinished scans never starting a repeat, and pending replacement reads
preserving previous freshness without reading the worker's unfinished timestamp;
negative results and cancellation override that fallback. They do not execute
native threads, sockets, DNS, PAF, ABI or layout.

The earlier simplification through bcbf30d added sixteen checks beyond the 167-check remote-Quit stage:

- `test_ui_resources.py`: all resource XML is well-formed, local CXML style/template/texture
  references resolve, texture files exist, and inner `textobj` bindings are explicit. This
  parses XML; it does not compile an RCO or render PAF. The locale check reproduced unescaped
  ampersand/less-than attribute errors before correction, with decoded labels preserved.
- `test_network_lifecycle.py`: module/allocation/Net/NetCtl failure cleanup, successful and
  repeated initialization, shutdown order and idempotence, with native calls mocked.
- `test_application_cache.py`: invalidation, bounded reads, shorter refreshes, empty lists
  and rejected admission. It models copies in application elements, without C memory layout.
- `test_touch_events.py`: actual DS4/tablet contact handling for Down, stationary frames,
  movement to the origin, Up, ID reuse and out-of-range ID fallback. Coordinate sampling and
  transport are mocked. The old tablet path reproduced the stationary-Move failure.
- `test_mdns_bounds.py`: literal/compressed names and consumed offsets; invalid pointers,
  cycles, truncated labels and output capacity; valid Question/PTR/SRV/A and truncated record
  headers/data. Actual decoder/parser bodies are interpreted with byte arrays and mocked
  callbacks. No sockets, native memory/ABI or whole discovery lifecycle is executed.
- `test_video_scaling.py`: 30 fit/cover dimension cases covering zero/equal/narrow/wide
  sources, rounding/alignment and wide cross-products, including modeled integer casts.
  Decoder allocation, frame cropping and PAF presentation are outside the check.
- `test_video_crop.py`: actual crop/presentation fragment with byte pointers checks an
  exact 960×544 surface skips row copies, wider/taller surfaces keep exact crop pixels and
  untouched tail bytes, and dimensions/pitch/statistics remain correct. Six size/stats
  combinations model `memmove` and PAF callbacks; no GPU/decoder/native rendering is executed.
- `test_remote_quit.py`: one follow-up check preserves public null identity-path rejection
  before allocation after removing the worker's unused path copy. Existing launch/Quit
  checks continue to interpret the private helper with its shorter signature.
- `test_host_persistence.py`: an additional actual append/merge check covers 96 combinations
  of metadata, pairing, port/address preference and fill-only host/storage identity. Another
  drives the new-record copy tail into nonzero destination storage for lengths 0/1/254/255;
  the old source failed NUL termination at 255 for name/internal/external. File I/O/allocation
  remain mocked; this does not establish persistence durability or native memory behavior.
- `test_gamestream_worker.py`: actual worker admission/entry with serial pthread mocks;
  three nonzero errors at each init/stack/create stage reject work without invoking crypto,
  while successful creation joins and preserves three callback results. The old inline
  fallback failed all nine rejection cases. No real thread/stack/crypto execution occurs.

Network, cache, metadata-merge and video-scaling checks passed before and after their
refactors. These checks do not establish compilation, real threading, native UI, TLS/network
integration or Vita behavior; maintainer build/device validation remains separate.

The repeat audit adds `test_option_menu.py`: one actual-source check covers all
three native action callbacks, null userdata/callback, captured payloads and
delete-before-notify order (9 subcases), passing before and after consolidation.
C++ names/delete are normalized to serial mocks; PAF destruction/focus/native
transitions are not executed. The touch check additionally covers DS4 release,
tablet CANCEL_ALL and clearing contacts before/after sharing the dispatch helper.
The full gate passes 184 checks; compilation and Vita validation remain pending.

The pairing check interprets the actual verification helper with mocked EVP results (-1/0/1/2
at Init/Update/Final, 64 combinations); only success at all three stages may accept a proof.
`test_pairing_errors.py` adds ten source checks for typed local/OOM/security/PIN classification,
RNG/AES/RSA/certificate/parser/HTTP failure propagation, cleanup and final XML-response pin
rollback, server error payload/409, cancellation without a failure event and response-error reset.
The actual helpers and selected caller guards/API completion fragment are interpreted; pointer,
buffer, allocation, crypto, curl, XML and mutex behavior is modeled. This is not a complete
handshake or actual library/ABI/native-dialog/device validation. The recorded gate had 137 passes.
The server-trust checks interpret the actual X509 comparison expression with mocked comparison
results and check enrollment/rollback ordering. They do not execute OpenSSL, TLS or file I/O.
C grammar checks are not compilation or type checking.

`test_controller_light.py` adds ten non-build checks for controller RGB feedback and the two
optional stream overlays. It interprets the actual callback, accepted-start reset, snapshot getter
and normalized PAF update method: controller filtering, Off/stop/cancel/finished gating, fresh
black RGB on restart, black turning the light off, stale generation, unchanged-color deduplication,
missing widgets and no polling when disabled. It also checks capability/service wiring, update
without a new video frame, CXML layering/settings/localization and reproducible mirrored PNG masks.
Mask reproduction compares the complete IHDR and decompressed scanlines, checks chunk CRCs,
unfiltered RGBA dimensions/length, white RGB and alpha geometry/mirroring. It deliberately
regenerates with another zlib compression level: compressed PNG bytes are not a portable
pixel identity check. This reproduces the old byte-comparison failure without a build; the
2026-10-24 maintainer CI log stopped at that assertion before SDK/dependency setup.
Mutexes, pointer/struct copies, color vectors and widgets are serial mocks. These checks do not
compile CXML/C++, render PAF, run a host or verify real concurrency, Vita appearance/performance,
AppSettings persistence or actual game-generated RGB. See docs/UI.md section 4.10.

`test_host_persistence.py` interprets the actual metadata writer, three host-store mutations and
the successful-pairing completion fragment. Eight checks inject fopen failure, each of eight
fprintf failures (sticky ferror), buffered close failure and directory failure; verify a single
close of every opened file, unchanged INI fields, new/existing record status propagation and
pairing success despite failed metadata save. The three fprintf macros are expanded from their
source definitions; char arrays, struct pointers, directory calls and stdio are mocked. The
previous source fails 24 cases across six of these tests; that source gate had 108 passing tests.
No compiler/ABI, actual filesystem/flush, concurrency, native-dialog or Vita behavior is tested.
Atomic replacement, memory rollback and power-loss durability are outside this correction.

Host-store simplification (2026-10-23): the same interpreter follows the shared metadata,
append and save helpers. Three additional checks cover new/existing records, absent metadata,
default/custom ports, UUID replacement versus pairing's fill-only rule, storage-directory
selection, preserved paired/address-preference state, append failure and rejected input.
All 150 non-build checks pass. These remain serial source checks with mocked allocation,
directory and file operations; maintainer build/Vita persistence validation is pending.

`test_ps_button_state.py` interprets the shared PS reset and the existing tap-timing fragment.
Two checks cover clearing stale pending input without releasing the overlay guard/PS lock,
reset call sites, delayed single tap, double tap at the window boundary, and hold suppression.
Time and stream-stop calls are serial mocks; controller-bit masking is replaced by a no-op.
This does not execute the full input loop, ShellUtil, real concurrency or Vita Quick Actions.

`test_ime_cleanup.py` interprets Main's result/cleanup prefix across read errors, Cancel, Enter,
unknown buttons and present/absent poll registration. It requires one Term and conditional
Unregister before outcome handling, with both state flags cleared. The check passes before
and after the cleanup refactor. It mocks the dialog and call list, excludes address processing,
and does not validate native IME/module behavior or PAF. The combined source gate is 153 checks.

`test_remote_quit.py` adds 13 non-build checks for the confirmed conflict → Quit → launch flow.
It interprets service busy/completion/message/poll methods, the stream's pre-launch decision,
API conflict identity payload and native Quit helper. Cases include Yes/No, canceled/aborted
dialog results with stale Yes, GetResult/Init/Term failure and cleanup retry, immutable pending
confirmation, fresh/stale/absent/same-app IDs, local cancellation, pinned/paired admission,
`/cancel` request parameters, response freeing, parser/transport/refresh failure and a host app
still running after Quit. One adapter check covers forwarding the confirmed target unchanged.
Time, dialog/call-list, HTTP/XML, pointers and globals are serial mocks; the stream prefix stops
before key generation and actual launch. These do not establish native ABI, real scheduling,
TLS, Expat parsing, PAF appearance or host/Vita behavior. The cancel parser's actual C fixtures
cover success, malformed/missing/duplicate/false fields, DTD and server errors, but remain
uncompiled/unrun by the agent. The combined non-build gate passes all 167 checks.
The maintainer reports successful basic Vita testing on 2026-10-23; no per-case log was
supplied. This does not execute the C fixtures or close the fault/race validation gates.

**Historical host-list gate (superseded by Main checks above):**
`test_host_lists.py` interpreted the shared host-snapshot/identity helpers, actual Main/Search
refresh/token-lookup functions, Main Select/Clear All/count/delete and Search's canonical lookup
fragment. Nine checks model 40 saved/16 discovered hosts, discovery growth between count/copy,
shrink/empty/error preservation, conflicting UUID/MAC and port, selection following a moved UUID,
obsolete tokens, Select/Clear All and deletion past eight, and lookup after eight despite duplicate
names. Callback bindings are source-checked. PAF vectors, allocation, service reads, widgets and
action-bar exit are modeled; C++ template/member syntax is normalized for the serial interpreter.
That source gate had 117 passing checks. No compiler/ABI, allocator, real threading/snapshot consistency, PAF
scrolling/focus, native dialogs or Vita run is established. Backend discovery still holds at most 16.

Main startup crash follow-up (2026-10-22): the original host-list normalizer replaced the actual
PAF sized vector constructor with idealized allocation, hiding its uninitialized-capacity defect.
That translation is removed; the tests model the corrected empty-construction/resize path and
reject reintroducing the unsafe row count constructor. All 127 checks pass. Allocation remains
mocked: this is not a test of the installed C++ SDK or PAF malloc. Dump/disassembly evidence and
the required maintainer cold-start retest are in [MAIN_STARTUP_CRASH.md](../docs/MAIN_STARTUP_CRASH.md).

**Historical one-shot discovery gate (superseded by worker checks above):**
`test_discovery_lifecycle.py` interpreted the actual service Start/Stop, API bridge, native scan
worker/start/stop/shutdown and Search's immediate error branch. Nine checks model duplicate Start,
natural completion/restart, FINISHED before thread return, exact create/start errors with one
caller error, Stop before native worker entry/after completion, interrupted-scan cleanup and a
transient wait timeout. The previous native start code fails three cases while the current service/
API remain in place. All 126 non-build checks pass. C++ method calls are normalized; globals and
function-local scope, kernel/network calls and serial worker steps are mocked. No compiler/ABI,
real threads, PAF, sockets, blocked-I/O latency, permanent wait errors or Vita proof is provided.

The foreground checks interpret the source terminal-event predicate across all event/operation
combinations and the retained-result classification (including a successful empty app list).
They do not execute PAF dialogs, threads, event-ring delivery or the complete state machine;
dialog handoffs and overlap prevention still require maintainer build/Vita validation.

`test_event_queue.py` interprets the actual event_queue.c functions/header and the production
MoonlightApp::ProcessEventTask body. Twelve new checks cover 400 snapshot updates interleaved
with pairing/start/stop/close; ordered scan/error events; latest-snapshot merge order; owned
address/PIN/server-error payloads; producer updates while the head waits for worker completion;
ack-before-callback and no replay; ring reuse/reset; null/truncated addresses; Connect's existing
fallback; and explicit ordered-only overload without overwriting accepted events. The capacity
is 16 ordered entries plus two snapshot slots and one pending head; this does not promise delivery
for arbitrary critical-only storms. C struct assignment, pointer identity, fixed arrays, string
copies, sizeof and serial scheduling/mutex calls are modeled. C grammar parsing is not compilation,
type/ABI checking, real threading, PAF/native-dialog execution or hardware validation. Run the
maintainer's ordinary discovery/pair/Apps/launch/stop/restart smoke sequence after building.

The adapter lifecycle checks interpret actual Start/Stop/Disconnect and ForwardEvent method
bodies with mocked API calls. They exercise callbacks before and after API return, immediate
errors, no-host rejection and late Connect/Pair returns after closure. The initial Start/Stop
checks reproduced seven ordering failures before correction. These are serial ordering checks,
not C++ type checking, real-thread synchronization or PAF execution.

The disconnect-admission checks interpret the actual API gate, entry points, cleanup worker
and shutdown with mocked mutex/thread/stream functions. They cover contention, pending admission
rejection (including cached app reads), duplicate/idle disconnect, pending-stream stop before
GameStream release, creation/stop failure rollback and shutdown yielding to a queued worker.
The C++ scoped-request syntax is normalized to its actual helper; destruction/unlock and atomic
operations are simulated. They do not validate compiler/ABI/RAII behavior, pthread scheduling,
real synchronization, curl/crypto lifetime on hardware or end-to-end DisconnectHost behavior.

`gamestream_xml_test.c` exercises the actual Expat parser API: entities/UTF-8,
empty and bounded lists, malformed documents, invalid IDs, root errors, verb
results, and session URLs. These fixtures require compilation by the maintainer;
the agent has not compiled or executed them. Example desktop command for the maintainer:

    cc -std=c99 -Iinclude tests/gamestream_xml_test.c src/moonlight/gamestream_xml.c -lexpat -o /tmp/gamestream_xml_test
    /tmp/gamestream_xml_test

These checks do not establish Vita networking, pairing or stream compatibility.

The opt-in [Vita disconnect/reconnect scenarios](runtime/README.md) give the maintainer
separate idle, active-stream, post-launch/pre-RTSP, in-flight HTTPS and common-c startup
DisconnectHost triggers through existing UI selection. All five are excluded by default and
are mutually exclusive. The active scenario waits for a
user-selected stream, requires STOPPED before CLOSED, and restarts the same app only after
paired reconnect and fresh Apps. Its checks include timer/busy gating, no restart before
closure, queued STOPPED after the adapter already reports DISCONNECTED, wrong host/app/state,
operation rejection/failure, timeout, user interruption and no repeat after PASS. These Python
checks interpret the actual source with mocked services/time, not Vita runtime or compilation.


The pending scenario's source checks interpret both its worker checkpoint and main-thread
flow. Atomics, services, time and worker yields are mocked; serial interleavings cover disconnect
while Launch is busy, expected -7 before CLOSED, no reconnect under the native error/OK dialog,
no early STREAM_STARTED, one-shot recovery and release on failure/shutdown/worker timeout.
A separate check interprets the actual post-response/pre-RTSP cancel fragment: failed launch
responses bypass the hook, cancellation returns -7, and an uncancelled path continues. These
checks do not compile C++ or establish actual memory ordering, real-thread/curl lifetime,
Vita error presentation or recovery playback. See runtime/README.md for maintainer steps.


The HTTP mode reuses the pending controller checks with its own log prefix and checkpoint label.
Additional actual-source C checks exercise callback filtering/complete headers, response-before-
checkpoint rejection, internal-handle isolation, no trace-data output, one-shot availability,
curl option setup-failure cleanup and removal of stack userdata before unlock. Mocked pointer
arithmetic/struct writes are used; no real curl, TLS, memory ordering, thread scheduling or C/C++
ABI is tested. The existing C grammar check still covers all trust/transfer/pairing fragments.
See the in-flight HTTPS maintainer procedure before claiming device/lifetime acceptance.


The startup mode now requires interrupted setup → STREAM_FAILED=-7 → CLOSED → native error OK →
paired reconnect/fresh Apps/same-app STREAM_STARTED. It rejects a first STARTED/STOPPED and
reports late_start=0 on PASS. The previous late_start=1 Vita result remains historical evidence,
not validation of this interruption change. The stage-filtered one-shot worker gate and source
checks cover busy admission, wrong/duplicate events, request failure, user-paced error OK,
timeout/shutdown release, the guarded callback and all 32 five-mode Boolean combinations.
This is not CMake configure or compilation.

The existing startup mode also accepts checkpoint 10 after successful video startup, before
audio startup/STARTED. Source checks require a complete three-slot pool/nonzero generation
before cancellation and cleared metadata of the same generation before reconnect. They cover
partial/absent pools, changed generation, bounded release wait and one-shot recovery. The test-only
observer's actual C body is interpreted over all 512 combinations of slot memblock/pointer/mapping
presence (loop increment/declaration normalized for the interpreter). Real allocator, native
unmap/free results, races and decoder/GPU lifetime are not established by these serial checks.
Stage 4 remains default; the stage-10 maintainer command and acceptance sequence are in
[runtime/README.md](runtime/README.md#after-video-allocation-checkpoint).

The production startup-interrupt checks interpret the actual mutex-protected publication,
stop, connection-ready and finish helpers. They cover cancellation before/after common-c's
reset, repeated stop/stage publication, success racing an interrupt, STARTED commit before stop,
uncancelled failures and validation errors before the first callback. They require no input/
STARTED after a winning cancel, owner-only stop exactly once for cancelled success, no second
stop after common-c's failed-init unwind, and owner reservation through terminal bookkeeping.
An additional actual-source check drives Apps' failure handler into the existing deferred-release
path, then exercises its three-tick delay, stale generation and active-Stream rejection guards.
All mutex/interrupt calls, atomics, services and time are mocked/serial. No real threads,
common-c/RTSP/TLS, PAF surfaces, compiler/ABI or hardware behavior is validated.

### Main discovery: maintainer Vita acceptance

The maintainer confirms PC discovery already works on Vita (2026-10-27). This procedure
covers the replacement Main list and is a regression/release reference, not required next
work. Detailed cases below have no individually reported results; do not infer them from
the basic acceptance or ask for a repeat baseline without a concrete regression.
When a focused pass is needed, use the current system build;
record its source revision, VPK SHA256, Vita firmware and Sunshine version. Build/install
instructions are in [INSTALL.md](../docs/INSTALL.md). No build or device run by the agent.

Keep a saved PC as a stable reference and use a separate, unsaved Sunshine PC for temporary
rows. If only one PC is available, record the cases that cannot be exercised as not tested;
do not delete existing trust/credentials merely to satisfy the setup. Use a disposable saved
record for deletion checks. A temporary row has no availability dot; a saved offline row
remains present even when its availability indicator changes.

1. **Cold start and stable rows.** Start with Sunshine stopped on the unsaved PC. Open Main
   and verify that saved rows appear without opening Settings. Start Sunshine: its temporary
   row should appear below saved rows without a Search action, spinner or modal. Leave Main
   idle through several five-second query cycles: no duplicates, flicker or focus reset.
2. **Expiry and return.** Stop the unsaved PC's advertisements while Vita remains connected
   to the LAN and Main stays active. Its row should expire after about 15 seconds of healthy
   discovery since the last received observation; saved rows must remain. Restart Sunshine:
   exactly one temporary row returns. Measure from the last observation when packet evidence
   is available, rather than treating the host stop click as an exact timer boundary.
3. **Pause and frozen age.** With the temporary row freshly observed, open Settings and then
   stop its advertisements. Stay in Settings longer than 15 seconds and return: the row
   should initially remain, then expire after its remaining active discovery time. Repeat
   with OptionMenu, Delete selection/Cancel and Add PC's native keyboard/Cancel. Opening and
   dismissing these controls repeatedly must remain responsive and must not crash.
4. **Focus and virtualization.** Keep a saved row focused while the temporary PC disappears
   and returns: focus must remain on the saved PC. Focus a temporary row and let it expire:
   focus should move to the nearest remaining row. If more than eight rows are available,
   scroll below the first screen and repeat; unchanged rows should retain their viewport.
   Equal names on distinct endpoints must not merge; repeated announcements of one endpoint
   must not add duplicates. Mark unavailable multi-PC cases as not tested.
5. **Selection and persistence.** Select the temporary PC: it remains unsaved through
   Connect/PIN. Cancel PIN or fail pairing and return directly to Main: no new saved record;
   it may still appear as a temporary discovery. Repeat through manual Add PC. Pair successfully:
   exactly one saved PC appears, with its server certificate; restart and reconnect without
   another PIN. An existing saved PC remains after cancelled/failed re-pairing.
   Reconnect to a paired PC, open Apps and return to Main: discovery resumes without duplicate
   rows. In Delete mode only saved PCs appear; row toggles and Select/Clear All must update
   visible and scrolled checkboxes. Delete confirmation Cancel preserves selection; OK removes
   only the disposable selected record. An online deleted PC may reappear as temporary.
6. **Overlay, suspension and streaming.** Open system UI, suspend/resume, and return to Main:
   input and discovery should recover without a query burst or stale row activation. During
   Apps/PIN/streaming and paused controls above, verify absence of this app's outgoing mDNS
   queries using a LAN capture that first demonstrably sees its active-Main queries to
   `224.0.0.251:5353` for `_nvstream._tcp.local`. Allow an in-flight query at transition.
   A quiet console or unchanged list alone cannot prove that queries stopped. Without a
   suitable capture, report UI recovery separately and leave network-pause evidence pending.

Report each numbered case as pass, fail or not tested, with the action/expected/actual result
for a failure. Attach only the relevant console excerpt or packet timestamps when available;
logs are console-only through the existing Debug log switch. This is a discovery regression
pass, not a repeat of the accepted general stream or release smoke test. Settings → Licenses
and credits wrapping, end-of-page scrolling and return navigation remain a separate UI check.
