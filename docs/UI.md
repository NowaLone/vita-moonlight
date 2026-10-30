# UI guide

How the Vita Moonlight PAF interface is built, which rules keep it looking like a native Vita app, and the
measured numbers behind every layout decision. Read this before changing anything under `cxml/`, `src/pages/`,
`src/option_menu.cpp` or `include/pages/`.

Companion documents: `AGENTS.md` (hard rules for agents), `ROADMAP.md` (plan and hardware checks), `README.md`
(overview and build).

**Maintainer acceptance, 2026-10-27 [hw, user-reported]:** replying “всё” to the four-item
question, the maintainer confirms Licenses and credits, Add PC/checkboxes/Delete, Debug log
preference retention after restart and compact stream statistics are checked and working.
This supersedes their earlier basic-validation TODOs below. Fault/race cases, independent
statistics benchmarks and the separate DS4 shape revision were not in that question.

**Main background discovery, 2026-10-23 [code; basic Vita acceptance 2026-10-27]:** Main now owns the
combined saved/temporary PC presentation. Search PC and its button, resources, strings and
callback restoration branches are removed. The current behavior is specified in
[Main background discovery](#main-background-discovery--2026-10-23). Dated Search evidence below
belongs to the former interface; it does not verify the replacement.
The maintainer confirms “поиск пк давно работает” **[hw, user-reported, 2026-10-27]**.
Do not reopen basic discovery without a concrete regression; this confirmation does not
itemize every timing, focus or pause/fault case below.

**Current-state review, 2026-10-22:** foreground progress uses PAF CommonGuiDialog
`s_dialogTextSmallBusy`; errors/Delete confirmation use SceMessageDialog. The maintainer
accepted the compact busy and pairing appearance; ordinary handoffs/stop have scoped logs.
Main/Search/Apps use page-owned dynamic snapshots (backend discovery 16/apps 64). Typed pairing
errors and later wrong-PIN → separate 409 attempts → successful pairing/Apps are recorded in
API audit §6.10. Dated investigations below preserve earlier implementations, failed experiments
and test counts; obsolete progress APIs/diagnostics and “next” requests are historical.

System infobar during streaming: [research and implementation notes](STREAM_INFOBAR_RESEARCH.md)
compare NetStream's AppMgr calls with the Stream lifecycle **[code]**. A valid Stream page requests
hidden through `MoonlightApp::HideStreamInfobar()`; its destructor requests visible before returning
to Apps. `MoonlightApp::Shutdown()` also restores the bar independently of stop-event delivery.
Failed restores remain pending for the next cleanup request; requests/results use console-only
`[Infobar]` diagnostics. No per-frame requests or local controls/touch bindings are added. User
confirmed the feature works on Vita on 2026-10-19 after commit `85899c5` **[hw, user-reported]**.
Individual lifecycle/failure-case results were not supplied; the full matrix remains in `ROADMAP.md`
**[open]**. No build or hardware test was run by the agent.

The opt-in `MOONLIGHT_SYSTEM_APP` prototype switches the PAF runtime to
`Mode_Application` after `SampleInit()`, initially following BHBB **[code]**. After
the user's startup allocation failure, its surface/text-surface pools are reduced
from 8/4 MiB to 4/1 MiB to leave room for Moonlight's separate newlib heap **[code]**.
The artwork follow-up now raises only the surface pool to 8 MiB under the current
64 MiB default system budget; text stays at 1 MiB. The reason, limits and pending
Vita gate are in [§5.7](#57-music-style-application-artwork--2026-10-30).
The original log does not identify the failed allocation's caller. On `7e20e94`,
the user confirms startup no longer crashes and Main/Settings work; Settings
open/close logs return USER_RW free space to its earlier value **[hw, user-reported]**.
The user also confirms launch without closing the Vita game and return to its same
session on the tested device **[hw, user-reported]**.
It retains `graphics_option=7` and the existing
CXML/page geometry. This is an experimental runtime profile; remaining native dialogs,
AppSettings persistence, infobar restoration and streaming presentation need Vita checks
**[open]**. See [system-mode notes](SYSTEM_APP_MODE_RESEARCH.md#prototype-on-codexsystem-app-mode).

Evidence tags used below:

- **[hw]** verified on a real Vita.
- **[shot]** measured from a Vita screenshot (a reference app or this app); not re-checked on hardware.
- **[code]** read from the source; not a claim about how it looks.
- **[open]** not verified; do not treat as fact.

LiveArea current layout (2026-10-26): `MoonlightApp` owns `LiveAreaService`,
which publishes the last connected PC in frame7 and its first six app names in
frames1–6 **[code]**. Changing labels are accepted on the maintainer's Vita
**[hw, user-reported, 2026-10-24; profile/logs not supplied]**. On 2026-10-26 the
maintainer replied “всё ок” to fresh VPK installation, replacement icon/startup,
PC/app labels, card activation and closure/reboot retention **[hw, user-reported]**.
The confirmation follows source revision `6e1a893`; tested artifact hash,
firmware and per-profile results were not supplied. Exact geometry and the wider
empty/stale/busy/cancel/error matrix remain **[open]**; see [LIVEAREA.md](LIVEAREA.md).

The a5 paper is 840×500 at screen (60,44), origin (480,294). App frames are
480×68 with a 68 px vertical step; frame7 is 360×210 **[code, supplied RCO]**.
App rows use Browser's original 472×48 `LA_window.png`, losslessly indexed as
`app_row.png`: black body alpha 97/255, antialiased corners and thin perimeter
(top RGB 53/alpha 106, bottom alpha up to 118) **[code, decoded resource]**.
Offsets x=6, y=2 give first-row bounds x=70…542, y=140…188; source visible bounds
are [1,1,471,47) **[code]**. The Browser screenshot row-edge fit is near (70,140)
**[shot]**. The existing Moonlight `icon0.png` is packaged again as `app.png`,
without a duplicate source file, and displayed at 32×32 **[code]**.
Icon replacement correction (2026-10-26): after the reported `0x8010113D`, the
maintainer's new 128×128 icon was found to be RGB/color type 2, including both
icon destinations in the existing normal/system
VPKs. It is now 8-bit indexed/color type 3 without alpha; all 74 RGB colors and
decoded pixels are preserved **[code; existing format check failed before and
passes after conversion]**. Fresh VPK installation is accepted by the maintainer
on 2026-10-26 **[hw, user-reported; profile/package hash not supplied]**.
Its first-row box is x=80…112, y=148…180. Text starts at x=120: 8 px after the
icon, with left/right margins 50/16, 22 px regular white system text, vertical
centring and ellipsis **[code; native alignment/scale/focus open]**.

Frame7 uses the same Browser artwork adapted to 280×158 at x=580…860,
y=330…488, preserving 8×8 corner patches and border thickness **[code]**.
Its width matches `startup.png`; the native gate outer box is 292×170, so exact
focus-border matching remains **[open]**. The transparent 80×80 PC icon is centred
above its 22 px name. The asset tool regenerates this card from `app_row.png`;
its optional Browser import verifies decoded RGBA equality **[code]**.
The maintainer's replacement `startup.png` (2026-10-26) is converted from RGBA
to 8-bit indexed 280×158 PNG with 256 colors and `tRNS` transparency **[code]**.
Palette reduction is lossy: mean R/G/B/A errors are 0.081/0.041/0.110/0.025 out
of 255; alpha extrema remain 184…255. The format check rejects the RGBA input
and accepts the converted asset. Installation/basic startup-image appearance are
accepted on 2026-10-26 **[hw, user-reported; no pixel-level hardware comparison]**.

With no app names, frame2/frame3 show “Moonlight” (28 px white) and “Open source
game streaming client” (20 px #d0d0d0), regular, centred and without shadow in
the system font. These native XML strings have no targets; a connected PC card
remains visible. Short nonempty lists clear unused backgrounds/icons/targets.
Packaged defaults use the same welcome text; content revision is 11 and all
frame revisions are 6 **[code; build/Vita open]**. The original spotlight has no
painted text. Current `gd`/`gdc` categories skip native top-left caption creation;
see [the supplied shell trace](SETTINGS_UI_RESEARCH.md#shell-caption-admission-traced-2026-10-25).

Frame targets carry saved UUID/app IDs and enter the existing Main/PIN/Apps flow,
with fresh-ID selection and existing remote-Quit confirmation. Conflicting
foreground workflows reject external requests. Seven-frame publication is serial,
not atomic **[code]**. Geometry, asset provenance, installation history and device
checks live in [the LiveArea guide](LIVEAREA.md); the
[Browser resource comparison](LIVEAREA.md#browser-resource-comparison-2026-10-25)
records the copied artwork and limits of the empty Browser template.

Offline manual replacement (2026-10-29) **[code]**: the three placeholder images are
replaced with 12 English and 12 Russian 960×544 indexed PNG pages. All prose comes
from `msg_manual_*` IDs in the existing EN/RU dictionaries. Root pages are English;
`sce_sys/manual/08/` holds the complete Russian sequence for the native viewer.
The layout uses 48 px side margins, 36 px headings, 23 px body text and 21 px notes;
the authoring tool rejects overflow instead of clipping or shrinking translations.
No fake buttons, supplied screenshots or extracted Sony artwork are used. The
[LiveArea guide](LIVEAREA.md#offline-manual-replacement-2026-10-29) records authoring,
chapter order and remaining viewer/language/install checks **[open]**. No agent build.

Historical three-page manual packaging follow-up (2026-10-21): the maintainer's `529c3c5` asset update
removed `sce_sys/manual/004.png`, retaining `001.png`–`003.png`. Its stale explicit CMake entry
caused the reported VPK packaging failure after SELF creation. That entry is now removed
**[code]**; all 15 source-file entries in the VPK manifest exist and its manual list matches
the three current pages. No assets are restored or edited. This is a source/manifest check;
VPK packaging/install was not separately reported. The subsequent stage-4 startup-interruption
log is scoped below; other hardware checks remain **[open]**. No agent build.

## 1. Principles

1. **Look like a native Vita system app.** PAF + CXML for pages, `SceAppSettings` for settings, `SceImeDialog` for
   text input, `SceMessageDialog` for confirmations. No custom keyboard, no custom settings screen.
2. **Match references by measuring, not by eye.** The references are PS4 Link (flow-page and list layouts),
   the system Photos app (selection mode, popup, selection bar) and the NetStream / `vitasdk-paf-component`
   samples (templates, speech balloon). Take 960 x 544 screenshots of both and compare pixels (section 7).
3. **Reuse a system `_common_*` resource only if it is known to exist and renders correctly.** The names already
   used in the XML are the only ones known to exist (section 4.6). Never invent a `_common_*` name. If no standard
   component is known, repeat the measured look with project styles and record the numbers here.
4. **XML first.** Layout and appearance live in `cxml/vita_moonlight_ui.xml`; code only fills content, state and
   events. Prefer choosing a template by state over showing or hiding widgets on a shared template.
5. **The UI never owns streaming or backend logic.** Pages call `MoonlightApp` services; backend events come back
   through the queued main-thread callback; no UI is touched from a worker thread.
6. **Say what was verified.** A number taken from a screenshot is not hardware-verified. Tag it, and update the tag
   when it is re-checked.
7. **Small, reversible changes.** One visual decision per commit; put the measured numbers and their source in the
   commit message and in this guide.

### Main background discovery — 2026-10-23

The maintainer explicitly permits **non-modal discovery on active Main** as an exception to
sequential foreground work. Connect/Apps/launch and PIN/error ownership remain unchanged.
The [official Wi-Fi investigation](WIFI_BACKGROUND_SEARCH_RESEARCH.md) supports one page with
saved/discovered rows and asynchronous scheduling. Its private AP APIs, fixed row counts,
70 px geometry and local spinner are not copied. Focus/expiry choices below are Moonlight
policies, not recovered Sony behavior.

- Main keeps saved hosts in store order, then appends distinct temporary discoveries. There
  are no section labels, search counts, progress strings or spinner. Add PC/native IME and
  the Delete/Settings corner remain; the Search button and page are gone. Manual entry is now
  the top-left PC-plus header button (see §5.1).
- `template_host_list_item_discovered` has the same **80 px [code]** row and title/address/PC
  icon coordinates as `template_host_list_item`, with no availability plane. Only saved hosts
  enter `HostService::CheckAvailability`; their TCP freshness/15-second repeat/30-second expiry
  are unchanged. A discovery is not a successful TCP check or an authenticated host.
- A single backend pthread worker (64 KiB stack) is created on first activation and retained until final
  application teardown. Inactive it sleeps on a condition variable with its socket closed.
  While active it sends the existing mDNS query immediately and **5,000,000 µs [code] after
  the previous send completes**, polling nonblocking packets between sends. Monotonic process
  time schedules the next send; delayed cycles do not accumulate catch-up work. No per-query
  thread/PAF job or timed worker recreation is used.
- Results are retained between queries and activations. A temporary endpoint expires after
  **15,000,000 µs [code] of active healthy polling since its last observation**. Pause, cancelled
  generations and detected socket/send/receive failure do not advance this age; recovery
  resumes it. Silent packet loss still ages results. Saved records never expire this way.
  Query/receive failures close the socket and retry at the next five-second deadline; identical
  repeated failure codes are logged once until recovery. No discovery error modal is opened.
- The worker alone owns socket/parser state. A dedicated pthread mutex protects control,
  generation/revision, observations and complete fixed-capacity publications (existing backend
  limit **16 discoveries [code]**). `HostDiscoveryService` caches coherent value copies on the
  main thread. `MoonlightApp::ProcessEventTask` polls those publications and queues a separate
  coalesced `DISCOVERY_CHANGED` invalidation. Dispatch rejects cancelled generations and any
  current page other than Main; Main also checks discovery eligibility before touching widgets.
- Main's existing deferred initial list warm-up gates activation. Leaving Main, OptionMenu,
  Delete mode, IME, Settings, foreground busy/error ownership and system UI overlay request
  cancellation. AppMgr overlay state is read at **100 ms [code]**; an unavailable state blocks
  discovery. Main renews a **250 ms [code]** backend lease while eligible. If PAF callbacks stop
  during suspension, the worker checks that lease before further network work and closes its
  socket when it next runs. This supplements explicit Stop without another lifecycle thread
  or consuming system events owned by PAF. Native suspend/resume timing remains **[open]**.
- `Stop()` invalidates service delivery immediately and only requests cancellation. UI never
  joins/waits for the worker. Connect's existing job waits for socket cleanup before its usual
  availability barrier/backend call. IME/Settings defer opening until a main-thread idle poll
  confirms worker cleanup; no polling sleep or search modal is introduced. Final teardown,
  after the PAF run loop, joins the dormant/finishing worker before network shutdown.
- Identity uses real UUID, then real MAC when both sides provide them, then matching usable
  internal/external route and port. Equal names do not merge discoveries. Current mDNS supplies
  no UUID/MAC; no background authentication or speculative identity is added.
- Main computes desired rows and applies only necessary `DeleteCell(..., 1)`, `MoveCell` and
  `InsertCell(..., 1)` edits between `BlockSync`/`UnblockSync`. These methods, `GetListItem`,
  `Widget::IsFocused` and `ListView::SetFocus` are declared by the installed PAF headers.
  Unchanged rows keep tokens/widgets; metadata updates fill existing items. Availability
  updates change only textures. Surviving native cells keep ownership of focus/viewport;
  a removed/retemplated focused row selects the same PC if present, otherwise its nearest
  remaining index (last row when the old index is beyond the end). This is the intended
  source behavior; native focus/scroll effects of edits still require Vita validation.
- Row callbacks use page userdata and tokens, not element addresses. Removed/retemplated
  tokens are invalid before native edits; mode and saved-state transitions replace affected
  templates. Selection checkboxes are resolved from currently generated items instead of
  keeping pointers across virtualization. After `SetName()` they must be resolved by their
  current row tokens, not original CXML IDs. Select/Clear All updates them without rebuilding.
- Clicking a temporary row captures a value copy and enters ordinary Main connection,
  which stops discovery. It does not save the PC. Discovered/manual hosts stay temporary
  through `/serverinfo` and the PIN page; only successful PIN/HTTPS pairing creates/updates
  the paired record and then writes its server certificate **[code, 2026-10-28]**.
  Cancel/error creates no new saved record; an already saved PC remains on failed re-pair.
  Authenticated paired reconnections may update existing metadata. Persistence errors remain
  separate from pairing success. LiveArea publishes the new saved UUID after pairing, before
  the Apps snapshot. No new pairing-cancel record cleanup or storage migration is needed.
  Pairing/Apps return directly to Main, which
  restores list activation and its callback. The completed successful PIN page remains removed.
- Delete mode contains saved rows only; temporary rows return afterward. A deleted online PC
  can reappear as temporary, without a dot. Delete is not a network blocklist.

Non-build checks interpret the actual worker/control/expiry/publication, Main eligibility,
merge/token/selection and cell-edit logic, plus main-thread event dispatch.
Serial clock/kernel/socket/vector/UI mocks do not prove real concurrency, native ABI, PAF
rendering or device responsiveness. Basic discovery is user-accepted (2026-10-27).
Detailed cases without individual results remain **[open]**: empty and
>8-PC startup; appear/disappear/reappear; same names/duplicate endpoints; focus/scroll during
insertion/removal/reordering; temporary-to-saved; repeated paired connection and PIN cancel/error;
Delete/IME/OptionMenu/Settings; system overlay/suspend/resume; no queries during streaming.
No agent application/resource compilation, packaging or deployment.
The 2026-10-28 persistence correction additionally requires maintainer validation of
discovered/manual PIN cancel, wrong PIN/network failure, success and restart/reconnect.
New checks cover deferred writes, pin destination/save ordering and persistence errors
without converting proven pairing success into failure; the full source gate is 262 checks.
The [regression reference](../tests/README.md#main-discovery-maintainer-vita-acceptance)
specifies setup, observable results, frozen-age timing and the packet evidence needed to
distinguish a paused worker from an unchanged list. Use it for relevant regressions or planned
release coverage, not as a new baseline gate for the accepted working feature.

**Linker follow-up, 2026-10-23 [maintainer build log; correction is source-only]:** the
initial Main implementation instantiated `std::vector<uint32_t>` and the Vita link failed
on undefined `std::__throw_length_error(char const*)`. The token scratch buffers now use
empty-constructed `paf::vector<uint32_t>`. Cell deletion compacts forwards, insertion shifts
backwards after `push_back`, and a move shifts the intervening tokens in place. No `insert`
from the installed PAF vector (which moves the overlapping range forwards), exception stubs,
linker flag changes or sized PAF constructors are added. The source check now interprets these
actual mutation branches as well as the planner. Agent build/compilation remains prohibited;
maintainer relink and native focus/scroll acceptance remain **[open]**.

**Discovery pause crash, 2026-10-23 [dump/source; corrected runtime unverified]:** pressing
`(...)` stops discovery before opening OptionMenu. In supplied
`psp2core-1792782876-0x0000e63259-eboot.bin.psp2dmp` (gzip SHA-256
`284c5ed67efc0fdd83411352754011eaca1c32ef72767905d470d4cfbfd6c3c6`), the
faulting thread is **mlmdns**, data abort `0x30004`, PC `0x8125716e`, R6=0.
The existing system ELF maps that PC (RX delta `0x4d000`) to
`pte_osSemaphoreCancellablePend+0x16`, `ldr r7, [r6, #8]`, after loading a null
pthread control pointer from thread-local storage. Stack return addresses map through
`sem_timedwait` / `pthread_cond_wait` to `discovery_thread`'s inactive wait. Main is waiting,
so this is a discovery-thread pause failure, not evidence against speech-balloon geometry.
Core module RX/RW sizes `0x296508` / `0x73114` match the existing system VELF; normal differs.
System debug ELF SHA-256 is `f26f558e805a5973d3491451afb79b594c640f6ca3e5f3f6f01b952eec912542`.
The faulting code page is absent from the core: the relocation/source mapping is corroborated
by sizes and stack, not a byte-for-byte installed executable or exact Git-revision proof.

The worker had been created with `sceKernelCreateThread`, which did not establish the
pthread runtime state consumed by the cancellable condition wait. It now uses checked
`pthread_attr_init` / 64 KiB stack setup / `pthread_create`, with attribute cleanup on both
create success/failure and `pthread_join` only at final teardown. POSIX setup errors remain
negative at the background Start boundary. The Connect job's cleanup barrier also avoids
`pthread_cond_wait`: PAF job threads are not guaranteed pthread state, so it uses the existing
worker-only 10 ms native sleep/locked-idle polling pattern. UI Stop remains nonblocking;
query cadence, retained snapshots, generation and OptionMenu resources are unchanged.

The earlier serial kernel mocks did not model this pthread TLS requirement. Checks now
require pthread creation before the worker condition wait, cover attribute/stack/create failure
cleanup/retry and final join, and execute the foreign-thread-safe Connect barrier. These are
source models, not native pthread/PAF execution. No agent build/compile/deployment; maintainer
rebuild and repeated `(...)` open/dismiss, Delete, IME/Settings, connect and suspend/resume
checks remain **[open]**. Raw dump, extracted memory and generated binaries stay out of Git.

### Sequential foreground workflow — maintainer direction, 2026-10-20

**Current implementation, 2026-10-21:** the compact PAF busy-dialog follow-up below supersedes
the historical SceMsgDialog progress-window descriptions. Error/confirmation dialogs keep SceMsgDialog.
The temporary workflow/timing and job-lifetime traces described below were removed after the
maintainer's successful run; they remain documented as historical evidence, not current output.

Target: one action → native WAIT during a long step → completed operation/dialog teardown →
result or next page. Conflicting selection/navigation must stay blocked until success, failure,
or cancellation with local cleanup. A cancellation request alone does not release the operation.
Pairing keeps its visible PIN page as the interactive step, with explicit cancellation; a generic
WAIT must not hide the PIN. Normal stream transport/render/input threads continue during playback.

Blocking control requests run inside the operation's worker/job while the PAF main thread keeps
dialogs and lifecycle events responsive. Completion events are internal delivery to that thread.
This implements a sequential user workflow; adding independently overlapping foreground requests
or a new general-purpose asynchronous subscription architecture is not the target.

**Source implementation, 2026-10-21; build/Vita validation pending:** ConnectionService owns
one foreground operation across Connect, ApplicationService refresh and stream launch/setup.
It opens native WAIT before starting the operation and rejects overlap or WAIT initialization
failure. Connect/app-list jobs publish their returned result with release/acquire ordering;
their completion cannot reach the page until the backend call returns and WAIT close is requested.
The result also supplies a completion if the corresponding queued event was dropped. Launch
retains the stream worker and waits for STREAM_STARTED/FAILED/STOPPED, then requests dialog close.
Reservation is released before dispatch so Connect → Apps → app-list loading can proceed.

Base blocks page opening and ordinary Back while this owner is busy, including connection
error dismissal. Connect retains its native error dialog; the later text-policy follow-up below
moves Apps/load and launch errors into native OK dialogs too. Enqueue/start failure closes WAIT before releasing
ownership. The interactive pairing page and its explicit Back cancellation remain separate;
no generic WAIT covers its PIN. Stop/Disconnect APIs and broader lifecycle races are not covered
by this three-operation reservation. Pages still own presentation/navigation.

Diagnostics: `[Workflow] begin operation=N` / `complete operation=N ...`, with Connect=1,
Applications=2, Launch=3. Verify successive WAIT handoffs, failures, blocked Back/repeated
activation and transition into playback on Vita.

**User feedback / source follow-up, 2026-10-21:** after `e838d91`, the maintainer saw the
wait window only during stream launch, while Connect/Apps still displayed page status.
The page calls did still write progress text; they are now removed/hidden for saved/manual
Connect, Search selection, Apps loading and launch. Pairing success no longer says it is
loading apps behind the Apps page. Search `SetStatus()` explicitly shows the widget again
for error/discovery/idle states after hiding it during connection.

ConnectionService's progress dialog now uses native `SceMsgDialog` USER_MSG with
BUTTON_TYPE_NONE and a static-lifetime message for the current operation: `Connecting to PC...`,
`Loading applications...`, or `Starting stream...`. At that revision it closed on completion
through an Abort/FINISHED/Term handoff (corrected below); errors/empty lists remained page state and
the PIN remains visible. The installed VitaSDK header defines this mode and button type;
this replaces the generic system WAIT text rather than adding a custom PAF dialog.
No artificial minimum display time is added. The reason for the unseen earlier short-step
dialogs is not established without logs. This source follow-up still needs build/Vita checks,
including the no-button dialog's appearance and immediate Connect → Apps handoff.

### Page text and native messages — maintainer decision, 2026-10-21

**[code; build/hardware pending]** Main/Search/Apps now contain static empty-list labels only,
shown when their list is empty (hidden during foreground progress/selection). No inline
search/keyboard/connection progress, `Select a PC`, delete-success result, `Connected`, or
`Stream stopped` text remains. CXML defaults also use empty-state labels; Apps no longer has
`Loading apps...` as its resource default. Pairing uses static instructions and the PIN only.

Errors use native OK dialogs: ConnectionService reuses its existing persistent message buffer,
WAIT teardown and dialog poll for Main/Search/Apps errors. Connection failures are owned by
the service; pages restore their empty-state visibility without showing a duplicate error.
A displayed/pending message is not overwritten by another error; that notification is logged.
Busy native dialog initialization waits for the existing dialog to release; other initialization
failures are log-only. No error text is drawn on a page if dialog initialization fails.
Invalid manual input waits for the error dialog to close before retrying IME.

Pairing retains its specific error messages/server Error 409 and OK → parent behavior; local
page-open/internal errors now use that same native dialog path. Failure to initialize it is
console-only. Instructions never change to `Pairing...` or `Paired`. Stream's opt-in statistics
and video status overlay are unchanged. Delete confirmation now uses OK/Cancel: OK deletes,
Cancel keeps selection, success returns to the refreshed list, failure opens a native OK error.

**PS4 Link reference [shot]:** user-supplied 960×544 JPEG, 2026-10-21. Pixel threshold measurement
of the bright text gives first-line ink y≈98–117, second y≈138–157; the next paragraph starts
y≈217–237, followed by y≈257–277 and y≈298–317 (descenders/compression add edge pixels).
Left ink begins x≈65–67, consistent with the existing x=64 text origin. This corroborates
40 px line spacing and a second paragraph 120 px below the first. The existing shared
`style_text_paragraph` supplies 26 px regular native PAF text, opaque white, 40 px pitch,
790 px wrap width. Font family/size cannot be established exactly from JPEG pixels alone;
the actual Vita rendering still needs comparison with the reference **[open]**.

Pairing uses that same paragraph style at layout origins (64,88) and (64,208), with localized
Sunshine-specific two-line instructions. PIN moves below the instructions to a 490×68 widget
at (64,368); the existing 48 px bold PIN style and bottom Back bar remain. Those positions are
source choices **[code]**, not measurements of Moonlight running on Vita. Validate wrapping,
PIN/bar separation, no status flicker, dialog error handoffs and Delete OK/Cancel on hardware.

**Pairing appearance [hw, user-reported, 2026-10-21]:** the maintainer confirms the new
pairing screen looks excellent on the tested Vita. Keep this layout. No new Moonlight screenshot
or installed revision/profile is supplied, so this is appearance acceptance on one device,
not a measured pixel match or verification of every pairing/error state.

### Short progress-dialog investigation — 2026-10-21

The supplied Vita log shows successful native Init → connect result=0 → Term → operation 1
completion, then Init → applist count=4 → Term → operation 2 completion. Operation 3 reaches
stream setup/decoded video and the maintainer sees `Starting stream...`; the first two windows
remain unseen. No init failure is logged. The trace has no timestamps or dialog polling status,
so it establishes successful API lifetimes, not visible presentation or their durations.

**Source defect / minimal follow-up [code; Vita pending]:** normal operation completion called
`sceMsgDialogAbort()` unconditionally and ignored its result. The installed VitaSDK exposes
[`sceMsgDialogClose()`](https://docs.vitasdk.org/group__SceMessageDialogUser.html) separately.
The local SDK `api_message_dialog/user_message` sample closes BUTTON_TYPE_NONE with Close,
and the system-message example does the same for its wait dialog. NetStream/BHBB also use
normal Close for their native PAF CommonGuiDialog waits; that is a different API and is not
copied into this SceMsgDialog path. These references support normal closing, not a guarantee
about animation/visibility on this firmware.

ConnectionService now requests Close in RUNNING, waits for FINISHED, checks Term, and retains
operation ownership until Term succeeds. A request made before RUNNING is retried by the
existing PAF poll. Close errors remain pending and are logged without repeated identical logs;
Abort remains only for forced shutdown. Polling is registered at successful Init and retained
while the window is open. No minimum duration, sleeps, extra UI or protocol changes are added.

Targeted console diagnostics emit `dialog open`, `dialog first poll`, `dialog close` and
`dialog term` with operation/status/API result and elapsed_ms. There is one first-poll message
per operation, not a frame heartbeat. These distinguish a short lifetime from a late first PAF
poll; RUNNING alone still does not prove a frame was displayed. Repeat Connect → Apps → launch
and collect these lines. The visibility root cause and the effect of normal Close remain
unverified until that Vita follow-up. Eight existing Python checks do not execute these dialogs;
no build or hardware run was performed by the agent.

### Compact PAF busy dialog — source follow-up, 2026-10-21

**Evidence:** the next Vita log measures Connect first poll at 15 ms, close request at 1750 ms,
Term at 2602 ms; Apps first poll at 2 ms, close at 1531 ms, Term at 2383 ms. Both have successful
Close/Term, with about 850 ms from close request to termination. The maintainer sees the windows
late, just before closing. Opening/render-ready time is still not directly measured; RUNNING
does not establish visible presentation. This evidence does not prove all subsequent PAF frames
were responsive or identify a specific opening-animation duration.

**Maintainer-approved change [code; build/Vita pending]:** Connect, Apps loading and stream setup
now use `sce::CommonGuiDialog::Param::s_dialogTextSmallBusy` through ConnectionService. This is
the small native PAF spinner/message box without Cancel shown in the supplied BHBB screenshot.
The reference is local BHBB `9e615e9186bf7ca5fb985dc06c1a5e06c47f24f5`,
[`common/dialog.cpp`](https://github.com/Ibrahim778/BetterHomebrewBrowser/blob/9e615e9186bf7ca5fb985dc06c1a5e06c47f24f5/common/dialog.cpp)
(`OpenPleaseWait` without Cancel and `Close`), corroborated by NetStream's same helpers. The
large official-app screenshot resembles a cancellable busy dialog; its exact API is unconfirmed.

Before Show, the service checks/loads `SCE_SYSMODULE_INTERNAL_COMMON_GUI_DIALOG`. The module
stays loaded for the application/PAF lifetime, as in the references; its stub was already linked.
Show uses `g_plugin` and PAF wide-string content on the main thread. A failed module load or Show
rejects starting the network operation and logs the failure; Connect reports a native progress-dialog
error instead of suggesting a PC/network failure. The existing reservation, worker
result publication and main-thread event delivery remain. Messages still describe Connect,
Apps and stream start; no custom CXML imitation or minimum display duration is introduced.

The service retains its slot while busy and calls the native PAF `Dialog::Close(slot)` once at
completion, discarding its return and releasing the logical slot, as in BHBB/NetStream.
The supplied native implementation does not produce a status code (see the ELF investigation
below); the earlier negative-result retry has been removed. PAF owns visual cleanup/animation;
logical slot release does not establish that the final closing frame has been presented.
This API does not expose SceMsgDialog's FINISHED/Term contract, so do not poll it using
SceMsgDialogGetStatus or invent an animation-ready condition.
Next-step dispatch occurs only after backend completion (Connect/apps) and logical slot release.
Shutdown also closes the owned PAF slot. No callback is attached to this noninteractive wait.

Native SceMsgDialog OK errors and Delete OK/Cancel, the accepted static pairing layout and
stream statistics are unchanged. Regression checks: compact wait appearance/latency, Connect →
Apps → launch handoffs, busy input blocking, PAF busy → Sce error handoff and shutdown. Console
diagnostics are now `[Workflow] PAF busy dialog open/first poll/close` with slot and elapsed_ms;
no progress `dialog term` is expected. Eight existing Python checks do not run PAF or compile
this API usage. Appearance, speed and cleanup on Vita remain pending maintainer build/testing.

**Header compatibility follow-up [code; build pending]:** the maintainer's build fails in
the installed `common_gui_dialog.h`: missing Sony-SDK `kernel.h`. That umbrella header also
includes `appmgr.h` and unused ErrorDialog declarations requiring a Sony-only app ID constant.
ConnectionService now includes `include/platform/paf_common_gui_dialog.h`, a narrow declaration
binding for native Param/Show/Close using VitaSDK/PAF types. Param fields, callback enum and
function signatures match the installed upstream header; `arm-vita-eabi-nm -C` confirms the
Show callback signature, Close(int) and s_dialogTextSmallBusy symbols in the linked stub archive.
No fake implementation, replacement symbol, SDK edit or global compatibility headers are added.
This read-only symbol/header check is not compilation/link validation. The maintainer must
rebuild before the compact window can be tested on Vita.

**Compact busy appearance / launch [hw, user/log-reported, 2026-10-21]:** the maintainer
confirms the compact dialog now looks good. The attached trace identifies `profile=system`,
`system_app=ON`, embedded revision `ca359a25edf0`. It contains operation 3 first poll at 132 ms
on slot 2, close return `0xEE251690` at 5337 ms, then close return 0 at 5654 ms. Only after
that does operation 3 complete and StreamPage open. Launch/setup result=0, audio packets and
decoded video follow; PS double press stops the stream and all three frame buffers unmap
with result=0. This supports appearance acceptance and the tested launch/play/stop handoff.

The first Close return is negative when interpreted as int32, but no named native error or
root cause has been established. Return-value semantics and the repeated Close need further
review; do not label it a proven harmless/native error or change timing speculatively. The
trace omits Connect/Apps dialog open/close lines, so their full handoffs/latency are not newly
log-verified. This is one system-profile run, not normal-profile, failure, shutdown or stress
coverage. Its embedded revision does not establish inclusion of `279d35e` (the header fix);
no configure/build transcript is supplied. No new build or device test was run by the agent.

**Initial Close investigation [source/binary metadata; superseded below, 2026-10-21]:**
the installed ScePaf-RE header, pinned by vitasdk-paf-component to
[`b76d6ae`](https://github.com/GrapheneCt/ScePaf-RE/blob/b76d6ae00516b107d37e7e8a1a16211e3b729a07/include/common_gui_dialog.h),
and the newer locally available upstream revision
[`7b1d3b6`](https://github.com/GrapheneCt/ScePaf-RE/blob/7b1d3b6aca81131fd90c65b81f317909e4feda1c/include/common_gui_dialog.h)
both declare `static int32_t Close(int32_t instanceSlot)`. Neither specifies result codes or
whether another call is required. The project's narrow declaration matches that return type.

BHBB at the revision linked above and
[NetStream `f812de8`, `source/dialog.cpp`](https://github.com/GrapheneCt/NetStream/blob/f812de87f739a740ae71fa1c23cd5c788084530c/NetStream/source/dialog.cpp)
call Close once and clear their current slot without inspecting its result. This establishes
their usage, but does not prove that the native function returns void or that every negative
value can safely be ignored. The import metadata maps Close to NID `0xBC311DC0` in
SceCommonGuiDialog (library NID `0x4B4AAE97`); the installed stub confirms the symbol
`_ZN3sce15CommonGuiDialog6Dialog5CloseEi`. A stub contains no native implementation, and
[ordinary non-template C++ symbol names omit the return type](https://itanium-cxx-abi.github.io/cxx-abi/abi.html#mangling-function).
Thus symbol matching alone cannot verify the return contract.

Two available Vita core dumps contain that export at Thumb addresses `0xe01d4ced` and
`0xe052412d` (both text offset `0x2b6c` after clearing the Thumb bit), but neither includes
the memory page containing the function body. Their included CommonGuiDialog text pages
cover only the tail of the module. No decrypted native module was found in the inspected local
references. Read-only header/history, reference-wrapper, stub/NID and core-segment inspection
therefore cannot explain `0xEE251690` or justify changing the runtime return handling.

At this stage a decrypted native module was required; the following supplied-ELF inspection
supersedes that unresolved conclusion. No runtime change was made in the metadata-only stage.

**Supplied ELF / minimal correction [binary/source; build/Vita pending, 2026-10-21]:**
the maintainer supplied `common_gui_dialog.suprx.elf`, SHA-256
`e7c0cf0fc184f00930c345cc0d8bef7d730923da47ed82a0e529042e516efede`.
It is an ARM EABI5 ELF with executable PT_LOAD at VA `0x81000000`, file offset `0xe0`,
size `0xe66c`. The export table independently maps library `0x4B4AAE97`, function
`0xBC311DC0` to Thumb entry `0x81002b6d` (code offset `0x2b6c`). No firmware version
was supplied; these binary findings apply to this module, not every firmware.

Read-only disassembly establishes these return paths:

- Close at `0x81002b6c..0x81002ba6` looks up the slot through `0x810055ec`.
  A missing/invalid slot returns the lookup's zero, without a distinct error status.
- For an existing slot it calls `0x81006a50`, then decrements the positive internal counter
  at object offset `+8`. If the counter stays nonzero, it returns without normalizing `r0`.
- With the counter zero it updates widget state, calls the closing helper at `0x81005676`,
  and returns directly. That helper's normal epilogue at `0x81005904..0x81005914` loads the
  stack-guard value into `r0`, compares it to the saved guard and returns without replacing it.
  The mismatch path calls the fail stub at `0x8100a0d8`. Import tables identify
  `__stack_chk_guard` (SceLibKernel NID `0x93B8AA67`, referenced through `0x8100b460`) and
  `__stack_chk_fail` (NID `0x37691BF8`), matching the installed VitaSDK NID database.

Thus this Close implementation exposes internal register residue, not a meaningful signed
success/error result. The earlier `0xEE251690` is consistent with the stack-guard return path;
its exact runtime value was not independently captured from the guard. A later zero can mean
the slot is already absent. Neither return establishes visual teardown completion, and an
extra call can decrement the internal counter again if the object still exists. The previous
`result < 0` check/retry was a client defect, not evidence of a native close failure.

ConnectionService now calls Close once per owned slot and discards the return; it removes
the retry/error fields and releases unstarted operations immediately after requesting close.
The narrow header retains upstream's int32_t declaration with a discard-return warning.
Logs say `PAF busy dialog close requested` without reporting register residue as a result.
Backend-result gating, operation reservation, Show/module error checks, first-poll diagnostics,
native error/Delete dialogs and pairing layout are unchanged. No minimum delay or guessed
animation/status API is added, and the supplied native binary is not stored in the repository.

Diff/lifetime review and all eight existing non-build Python checks passed. Those checks do
not execute ARM code or PAF. Regression risk: the next step/error can now start after the
first close request, without the former accidental retry delay. Maintainer build/Vita checks
remain necessary for Connect → Apps → launch, failure-to-OK handoff, immediate job-start failure
and shutdown. Expect one close-request log per opened slot and no return-based retry; appearance
acceptance from the earlier run does not verify this new handoff behavior.

**Post-correction device trace [hw, user/log-reported, 2026-10-21]:** the new maintainer
log contains all three operations with the revised `close requested` diagnostics:

- Connect, slot 0: open at 2 ms, first poll at 15 ms, one close request at 1767 ms,
  then completion event 9/result 0.
- Applications, slot 1: open at 2 ms, first poll at 3 ms, one close request at 1547 ms,
  then event 15/result 4 and four rows (`after_delete=0`, `after_insert=4`).
- Stream setup, slot 2: open at 2 ms, first poll at 14 ms, one close request at 5187 ms,
  then event 12/result 0 and StreamPage. This run uses same-app resume, accepted RTSP,
  successful setup and the nongame decoder path in AppMgr mode 2.

There is exactly one close-request line per opened slot and no return-based close retry
in the supplied trace. This verifies the normal three-step logical handoff on the tested Vita;
the log alone does not measure visible opening/closing frames. It includes no build-revision
marker, failure-to-OK handoff, immediate job-start failure, application shutdown or repeat cycle.
These remaining checks and broader F5 races are not closed by this run.

PS double press requests stop; the owner finishes with result 0, the infobar is restored and
all three video buffers unmap with result 0. Playback quality is a separate open observation:
42 frames decode, followed by IDR waiting/drop-limit/request messages, and common-c reports no
audio traffic received. The trace contains no later decoded-frame recovery or audible-output
confirmation. Do not infer sustained video/audio success or a dialog-related cause. The ENet
interruption/control error 4 appears after explicit stop and is consistent with common-c's
`ConnectionInterrupted` → `EINTR` path (`Misc.c` / `ControlStream.c`), not evidence by itself
of an earlier network disconnect. This record changes documentation only; no agent build or
device test was run.

**Playback clarification [hw, user-reported, 2026-10-21]:** asked whether this attempt had moving
video and sound or a playback problem, the maintainer replies “всё нормально”. Observed playback
is accepted for this run. This does not explain the IDR/audio log warnings or establish sustained
quality measurements; no playback defect is confirmed and no streaming-code change is made.

**Diagnostic cleanup [code; build/Vita pending, 2026-10-21]:** at the maintainer's request,
remove temporary foreground begin/complete, busy-dialog open/first-poll/close timing traces,
their timestamp/poll fields and the now-unused process-time include. Connect/Pairing jobs no
longer print addresses or Run/Finish/destruction/cancellation lifetimes; successful enqueue
traces are removed, with enqueue failures retained. Pairing no longer logs the constructor
PIN/root or PIN-widget address. Error/fallback messages remain in Debug Log. Main/Search/Apps
list-population diagnostics, backend protocol diagnostics and streaming logs are unchanged.
Native dialog calls, operation gating, main-thread polling, result publication and pairing
cancellation are preserved; the pairing result local was used only for the removed log.
This is an output cleanup, not a new UI/protocol fix. Source/diff review and eight existing
non-build Python checks pass; no build or hardware test was run for the cleanup.

## 2. Screen geometry and the layout language

### 2.1 Zones (960 x 544, **[shot]**)

| Zone | y range | Notes |
|---|---|---|
| System status bar | 0 - 32 | drawn by the system (`graphics_option = 7`) |
| Header / title bar | 32 - 96 | `template_top_title_bar` is a 64 px plane here |
| List | 96 - 480 (384 px) or 96 - 544 (448 px) | `template_list_view_main` / `template_list_view_generic` |
| Bottom bar | 480 - 544 | 64 px; only where a page has one |
| Corner buttons | bottom-left / bottom-right, about 80 px circles | system `corner_button` styles |

Rows are 80 px tall and 960 px wide. The first row's top edge is at y = 96 and draws its own dark/light line pair
(y = 95 / 96).

### 2.2 Coordinates (**[hw]** for centre-origin, **[shot]** for the anchor values)

- PAF is **centre-origin**: with default anchor/align, `pos="0, 0"` is the centre of the parent; **+Y is up**.
- `anchor` picks the point on the parent, `align` picks the point on the widget that is placed there. Values:
  x: 0 centre, 1 left, 2 right; y: 0 centre, 1 bottom, 2 top. `pos` then offsets from that point (+x right,
  +y up, so a top-anchored widget moves down with a negative y).
- `adjust` (`layout_hint`, `layout_box`): 0 none, 2 fit to content. Patterns in use: text with `size="W, 0"` and
  `adjust="0, 2"` gets its height from its content; a button with `adjust="2, 0, 0"` and `size="0, 46, 0"` gets its
  width from its label; a `layout_box` with `adjust="2, 2"` wraps its children. `size` accepts 2 or 3 components.
- `layout_box` attributes in use: `anchor`, `align`, `pos`, `space` (gap), `adjust`, `layout_type` (1 vertical,
  2 horizontal), margins, `size`.
- At run time `SetPos(paf::math::v4(x, y, 0))` on a default-anchored widget (the speech balloon) takes the widget's
  **centre** in the same centre-origin coordinates **[shot]**.
- **Visible edge vs layout box:** a button's visible edge sits about 1.7 px inside its layout box (shadow and
  rounded texture) **[shot]**. When matching a reference, measure the visible edges on both screenshots the same way
  and subtract this inset; do not compare a layout number with a screenshot number.

### 2.3 Colour and alpha (**[shot]**, derived from measured pixels)

- In a `style_plane` the style `color` and its `planeobj` `color` **multiply, alpha included**. The same value in
  both squares it. Keep the style at `color="1, 1, 1, 1"` and put the real value in the `planeobj`.
- Blending is plain encoded-space `result = background * (1 - a) + colour * a`; there is no gamma step.
- `planeobj` colours are 0..1 (`(14, 27, 119)` is `0.055, 0.106, 0.467`).
- A 1 px plane works as a line. An RGBA PNG through `<texturetable>` and `<plane texture="...">` works
  (`bg.png`). Header separators now use the system `_common_texture_ruled_line` **[code, 2026-10-23]**.
- The earlier near-invisible system-line observation (1-2 RGB levels) predates the native-height
  correction. The supplied common RCO contains a 4 px-high image with transparent outer rows;
  both header separator planes now retain that height. Appearance remains **[open]** on Vita.

**Palette alignment, 2026-10-28 [shot/code; build/Vita pending].** The supplied
`2026-10-28-022659.jpg` Main screenshot has median RGB **(2, 8, 27)** in the
widget-free body rectangle **[64, 280, 896, 470)**. The same rectangle in
`texture/bg.png` has median RGB **(2, 8, 26)**. Native AppSettings now uses that
asset-derived **(2, 8, 26, 255)** solid background in `moonlight_settings.xml`,
replacing the inherited bright blue **(4, 21, 105, 255)**. It remains the real
Sony Settings UI, with its native controls, gradients and focus glow; this
matches the base palette, not the decorative texture. Pairing already uses
Main's `_bg_texture`; its bottom bar now reuses Main's translucent selection-bar
styles and two separator rows instead of the opaque PS4 Link blue styles.
The **64 px** bar, Back-button geometry, text and PIN remain unchanged **[code]**.
XML/reference checks do not establish native AppSettings tint or Vita appearance.

### 2.4 Text

- `style_text` needs its `textobj` attribute bound to the inner `<textobj id="...">`; unbound text styles are not
  allowed. `align_x` omitted is left, `1` is centre; `align_y="1"` is vertical middle; `word_wrap`, `ellipsis`,
  `enlarge_line_pitch="1"` with `line_pitch` for multi-line text.
- Font size from a reference: compare the cap height of a flat capital against known fonts in this app. 22 px gives
  17 px, 28 px gives 23 px (**[shot]**; the ratio drifts by about 1 px between sizes, so confirm by overlay).
- A text widget placed over a button (host rows) has not been confirmed on hardware to let touches reach the button
  (**[open]**, tracked in `ROADMAP.md`).

### 2.5 Identifiers and XML hygiene

- Widget ids must be unique in the resource. Style-local ids (`textobj` / `planeobj` / `bg_obj` / `label_obj` /
  `glow_obj`) repeat across styles today and that is fine.
- Templates that can appear on the same page type use **distinct child ids** (`image_button_host` vs
  `image_button_host_select`); code picks the id by mode.
- No XML comments inside elements: none exist in the project and they have not been tested with `psp2cxml-tool`.
  Put explanations in docs and commit messages.
- Escape reserved XML characters in locale attributes (`&amp;`, `&lt;`). All current
  resource XML files pass strict parsing; decoded labels retain their literal symbols.

## 3. Pages

| Class (`page::Type`) | XML page | Purpose | Back mechanism |
|---|---|---|---|
| `Main` | `page_main` | saved + temporary PCs, background discovery, inline Add PC, selection mode | none (bottom of the stack) |
| `Pairing` | `page_pairing` | shows the PIN, pairs as soon as it opens | bar button `btn_close_pairing` |
| `Apps` | `page_apps` | application list of the connected PC | corner button `btn_close_apps` |
| `Stream` | `page_stream` | full-screen video plane, black background, optional statistics overlay; no chrome | none (closed by stream events) |
| `OptionMenu` | `page_settings_bubble` | speech-balloon overlay: Delete, Settings | dismiss button over the whole screen |

Navigation **[code, 2026-10-23]**: Main -> OptionMenu -> Settings (native AppSettings) or
Delete (saved-only selection on Main). Selecting a saved/discovered PC or using inline Add PC
(native IME) -> connect -> Pairing or Apps -> Stream. Apps/Pairing cancel/error return to Main.
Successful Pairing is removed from the Base stack only after Apps opens successfully; if Apps
cannot open, Pairing stays with an error. Main callback restoration refreshes rows and reactivates
the list. The new routes and background integration need maintainer build/Vita validation.

**Historical Search navigation evidence:** on 2026-10-19 the maintainer verified Search ->
successful Pairing -> Apps -> Back -> Search and selecting a PC again. That evidence concerns
the removed Search page, not the new Main return path. Earlier pairing error evidence follows.

Pairing failure ends the current attempt **[code, 2026-10-20]**. After its native OK
error dialog finishes, Pairing returns to the existing parent PC page. Dismissing an
error never generates another PIN or queues another handshake; selecting a PC again
explicitly starts a new attempt. This replaces the previous automatic retry for every
non-network error, which repeatedly regenerated PINs on duplicate-session rejection.
Correct-PIN success navigation is unchanged **[code]**. User/log verified one incorrect-PIN
error → OK → Search and one duplicate-session error → Search, with new requests only
after explicit PC selection, on 2026-10-20 **[hw, tested Vita]**. After Sunshine displayed
its delayed failure, another selection produced a new PIN and waited at getservercert;
completed pairing/Apps was not yet shown at that stage. A later system 5db31a9 trace
(2026-10-22, API audit §6.10) now completes all five phases and inserts one app after wrong
PIN and two separate 409 attempts on host .154. Main return and other error types remain
**[open]**. The maintainer earlier
reports the discussed recovery flow now appears OK (2026-10-20, qualified user confirmation;
no new log or separate Apps result). Returning to Search does not cancel or reset the
host's pending pairing session.

Pairing protocol errors now display the host's GameStream XML `status_message` and
`status_code` **[code, 2026-10-20]**. For the tested duplicate-session response, the
native dialog is intended to show: `The PC returned a pairing error:` followed by
`A pairing session with this uniqueid already exists (Error 409)`. This is a server
response code, not the semantic pairing result (-1003). Wrong PIN, network, security
and internal failures retain their specific local messages. Missing server details
use the generic fallback. The maintainer confirms the duplicate-session reason with
Error 409 is visible in the Vita dialog on 2026-10-20 **[hw, user-reported]**; the
supplied log independently confirms server_status=409. Other codes and long/Unicode
message clipping/layout remain **[open]**. The OK → parent PC page behavior is unchanged.

Pairing error preparation **[code, 2026-10-23]**: `ShowPairingError()` formats the
message and delegates parameter initialization to `ShowSystemError()`. The latter
clears the user-message structure and calls the VitaSDK `sceMsgDialogParamInit()`,
which clears the complete parameter structure before setting its native metadata.
The redundant earlier clears were removed; messages, buttons and dialog lifecycle
are unchanged. Native regression validation remains with the maintainer.

Pairing page destruction now requests local cancellation through PairingService
**[code, 2026-10-20]**. A new connection also cancels any prior pairing before enqueue.
This is nonblocking on the UI thread; queued jobs skip work, and an active HTTP pairing
wait aborts through curl progress. It does not reset Sunshine's pending session. The
reported older-host wait behind an abandoned pairing request is F8 in the API audit.
The `e7e7166ae5db` system-profile log shows active getservercert cancellation (-11/-1006),
job Finish/destruction and successful subsequent connection/new PIN page
**[hw, tested Vita]** on 2026-10-20. Wrong-PIN and later empty-reply attempts also finish/release their jobs;
that empty reply remains accepted F6. A second-host trace also verifies local cancellation
and successful Connect, followed by a real duplicate-session 409 on immediate pairing
retry **[hw, tested Vita]**. The maintainer separately confirms ordinary correct-PIN
pairing opens Apps after the cancellation change **[hw, user-reported, 2026-10-20]**;
its successful phases are not included in that trace. Queued/later-phase cancellation,
shutdown, stress/alternating-host and normal binary-profile checks remain **[open]**.
No recurring main-thread heartbeat or changed PIN timeout is introduced.

Add PC is an inline control on Main; there is no Add PC page.

**Confirmed remote Quit, 2026-10-23 [code; basic flow accepted on Vita by maintainer]:**
when fresh host state rejects launching a different application, ConnectionService closes its
PAF busy slot and offers a native SceMessageDialog **Yes/No** confirmation. It warns that quitting
loses unsaved progress and ends other streaming sessions. No preserves the host session. Yes is
acted on only after a successful dialog result and termination, then the existing stream worker
shows the normal busy window while it quits the confirmed app and starts the selected app.
Apps activation and Back are blocked while the message or operation is owned. Initialization/
result failures never authorize Quit; shutdown clears pending approval. There is no custom CXML
popup, inline message or separate Quit button. Apps retains framebuffer-release handling; the
service now owns all asynchronous launch errors and the confirmation.

The worker rechecks the authenticated active ID; an already idle host launches normally, the
selected active app resumes, and a different unconfirmed ID needs a new confirmation. A matching
approved ID permits paired HTTPS `/cancel`; valid XML `cancel=1` and refreshed idle host state
are required before launching. Sunshine's host-wide endpoint cannot atomically enforce the ID
comparison, so a change between the last snapshot and `/cancel` remains a protocol race. Ordinary
double-PS stop, local cancellation and disconnect never call `/cancel`.

**Maintainer acceptance [hw, user-reported, 2026-10-23]:** after the implementation, the
maintainer reports “я проверил всё ок”. This accepts the requested confirmation/Quit-and-launch
flow on the tested Vita. No screenshot, per-case log, installed profile/revision or Sunshine
version was supplied; individual fault/error handoffs, host-state races and broader regression
coverage remain **[open]**. No agent build or device run.

IME result handling shares one cleanup sequence for success and read failure: read the result,
terminate the dialog, clear the open state and unregister its poll before handling the outcome
**[code, 2026-10-23]**. Abort-on-destruction, module ownership and retry behavior are unchanged;
source checks model the ordering, while maintainer build/Vita validation remains **[open]**.

**In-stream keyboard text (2026-10-27) [code; build/Vita pending].** The existing stream
IME retains its Enter/Cancel flow; system language selection is described below
(2026-10-29). Enter converts UTF-16 using
PAF's `common::Utf16ToUtf8` and sends one `LiSendUtf8TextEvent` with the byte length.
The old ASCII filter/keycode loop dropped Cyrillic/accents and confused text with Win32 VK
codes. Empty text sends nothing; conversion/queue failures are console-only and never fall
back to synthetic keys. The build asserts matching IME/PAF code-unit sizes. Source checks
mock conversion/transport for punctuation, five languages and a surrogate pair; native PAF
conversion, IME, host text reception and game compatibility still require maintainer validation.

## 4. Building blocks

### 4.1 `page::Base` (`include/pages/page.h`, `src/pages/page.cpp`)

- Owns the page stack. A page is `Base(page_id, back_button_id_or_NULL, open_transition, close_transition)`.
  Opening deactivates the previous page; destroying a page closes it and reactivates the one below
  only when that page is not in a navigation transition (including mid-stack PIN removal).
- If `back_button_id` is given, the widget with that id gets the default back callback (`CloseCurrent()`); it is shown
  when there is a previous page and hidden otherwise. A corner button or a normal button both work.
- `IsValid()` must be checked after construction (`new X(); if (!x->IsValid()) delete x;`).
- `page_stream` is opened with `graphics_flag = 0x80` and a higher draw priority (`Base` special-cases its id).
- Do not add a second page stack.

Unused `Id()`/`Root()` accessors were removed in the 2026-10-23 simplification
follow-up **[code]**. Existing page identity, scene ownership and navigation remain.

The repeat audit removes the unused `CloseType()`/`Type`/`GetType()` family, free
`page::Find()` alias and `Stream::Instance()` getter **[code, 2026-10-23]**. Pages
still use `Base::Find()`/`IsOpen()` by CXML ID and the same stack/virtual destructor.
These project classes are not native PAF interfaces or exported module APIs.

OptionMenu's three native event callbacks share `CloseAndNotify()` **[code,
2026-10-23 repeat audit]**: copy the callback/userdata, delete the menu, then
notify the parent. Null userdata and null callbacks remain tolerated. The ignored
constructor plugin/parent arguments were removed; Base still opens the same CXML
page. Popup geometry, focus, buttons and transition behavior are unchanged.

Pairing has no page-local started flag **[code, 2026-10-23 repeat audit]**:
private `StartPairing()` is called once by a valid constructor and still rejects
an empty PIN. The service owns the real pairing operation/cancellation; terminal
events retain their error/navigation handling without redundant flag writes.

Main shares its identical CONNECTION_FAILED/CLOSED switch body **[code,
2026-10-23 repeat audit]**: clear the local connection flag, restore empty-state
visibility through `ShowIdleStatus()` and reactivate the host list. Native error
ownership remains in ConnectionService.

### 4.2 Templates (`<templatetable>`)

| Template | Child ids | Used by | Purpose |
|---|---|---|---|
| `template_top_title_bar` | `plane_top`, `box_top_title`, `text_top`, `plane_top_separator` | Main, Apps | Settings-style plane/box/text header, centred 32 px bold title over the system ruled-line separator |
| `template_list_view_generic` | `list_view_generic` (960 x 448) | Apps | list that runs to the bottom of the screen |
| `template_list_view_main` | `list_view_main` (960 x 384) | Main | list that ends where the bar starts (y = 480) |
| `template_app_list_item` | `list_item_app`, `image_button_app`, `plane_app_cover`, `plane_app_fallback` | Apps | Music-style 960 x 90 cell; 840 px backdrop / 900 px focus |
| `template_host_list_item` | `list_item_host`, `image_button_host`, `plane_host_pc`, `text_host_title`, `text_host_desc` | Main | saved PC row: availability dot, PC icon, title and description |
| `template_host_list_item_discovered` | same scoped ids as the normal host row, without `plane_host_availability` | Main | temporary PC; same columns, no dot |
| `template_host_list_item_select` | `list_item_host_select`, `image_button_host_select`, `plane_host_select_pc`, `text_host_select_title`, `text_host_select_desc`, `checkbox_host_select` | Main (selection mode) | same row with a checkbox |
| `template_flow_bar` | `plane_flow_bar` + two edge planes | Pairing | translucent bottom bar sharing Main's selection-bar styles (no buttons) |

### 4.3 Styles (`<styletable>`)

Planes: `style_plane_selection_bar` (+ `_edge_dark`, `_edge_light`) for Main's Photos style selection bar
and Pairing's bottom bar; `style_plane_stream_black` for the stream backdrop.

Text: `style_text_header` (32 bold, centred), `style_text_paragraph` (26 regular, line pitch 40, wrapped),
`style_text_row_title` (28 regular), `style_text_row_desc` (22, 85% white), `style_text_pin` (48 bold),
`style_text_main_status` (22, centred; Main/Apps empty-list text),
`style_text_stream_statistics` (18, yellow, left/top, unwrapped, 20 px line pitch; streaming diagnostics).

The stream statistics overlay uses `plane_stream_statistics` (660 x 136, top-left offset 16/-12)
and `text_stream_statistics` (644 x 120, offset 24/-20, at most 6 explicit lines). The background is
black at alpha 0.65 with a white style multiplier. These are implementation values **[code]**,
not screenshot measurements; the maintainer accepts compact-overlay readability/operation
**[hw, user-reported, 2026-10-27]**. The old stray `ge>` text was removed when editing the resource.

The existing AppSettings key `show_fps` and `msg_show_fps` identifier remain; the visible label is now
`Display stream statistics`. `Stream::StatisticsTask` updates cached text/background widgets at most
once per second independently of arriving video, and is unregistered in the page destructor. The
same task polls cached stream health every 250 ms for the transient warning below. With the setting
off only receive counts/bytes, frame-number gaps and last-video time remain active; detailed
per-frame timing hooks and RTT polling stay off. The overlay
shows only video mode/payload bitrate, incoming/decode/PAF FPS, available RTT/variation, drop
percentages, average decode-call/PAF-queue timing and optional host min/max/average. Unsupported
or expired measurements are omitted. During a stall only current rates, available RTT and the
stalled-video state remain. Audio/CPU/stride/window/cumulative-counter details and permanent
`N/A` rows have been removed after the user's device screenshot showed excessive screen coverage.
The old 928 x 380 panel is superseded; the compact panel is user-accepted on Vita. PAF FPS
still measures texture submission, not physical presentation.
The setting's native AppSettings hint (`msg_show_fps_hint`) explains Video/Mbps, the three FPS
rates, RTT/variation, missing/pacer/PAF drops, average decode-call/queue timing, optional host
min/max/average and the stalled-video state. Its text and binding are source-checked; native hint
layout still needs a Vita check.
RTT is sampled outside PAF by the existing session owner, which also performs transport cleanup;
UI snapshots only copy cached statistics. There is no separate RTT thread. Queue timing includes
waiting to acquire the frame mutex.
See [STREAM_DIAGNOSTICS_PLAN.md](STREAM_DIAGNOSTICS_PLAN.md) for metric definitions and remaining work.

Stream warnings (2026-10-24, source only): a non-modal amber single-line PAF badge appears at the
bottom center, independently of `Display stream statistics`. The existing Moonlight poor-connection
callback or at least 5% missing frames in the receive window selects `Connection unstable`.
Only with one of those conditions, video payload below 50% of the configured bitrate selects
`Connection unstable: low video bitrate`; healthy static scenes never warn on bitrate alone.
No received video for at least one second selects `Waiting for video`, including waiting for IDR.
Warnings are suppressed for the first three seconds after session admission, persist while the
condition remains, and hide three seconds after the last unhealthy poll. An inactive/mismatched
session hides immediately; each new stream starts with cleared health and page state.
These are receive-path symptoms, not a diagnosis of Wi-Fi/host/Vita or physical-display stalls.
Worker callbacks only update locked, generation-checked state; PAF changes happen on its main-thread
call list, without new threads, dialogs, file I/O or per-frame logs.
The 480 x 44 badge has a 56 px bottom inset; its 464 x 28 centered text has a 64 px bottom inset,
20 px font and amber color, over the existing black/0.65 statistics background **[code]**.
Thresholds, appearance and fault/recovery behavior require maintainer RCO/application build and
Vita validation **[open]**. Source checks interpret policy, receive counters with statistics off,
generation/stop guards and the UI hold/recovery path with mocked time, mutexes and widgets.

Buttons and lists: `style_image_button_app` (Music-style app row, 32 px title and native focus),
`style_image_button_host` (shared PC-row background/glow; `tex_pc` is a separate 80 x 80 plane),
`style_button_option_top` / `style_button_option_bottom` (popup buttons), `style_list_view_generic`,
`style_list_view_item_generic`.

Repository simplification, 2026-10-23 **[code]**: removed the unreferenced fill/flow-note/title/body/
single-option styles, unused Main/Apps selected-index fields and unused Pairing dialog title/button
storage. Active templates, geometry, focus and native dialog messages are unchanged. XML reference/
text-style checks pass; this does not establish RCO compilation or native rendering.

Locale XML hygiene, 2026-10-23 **[code]**: escaped the ampersand in `msg_swap_xo`
and the less-than sign in `msg_swap_shoulders` so `cxml/locale/en.xml` is well-formed
XML. The decoded labels remain `Swap X & O for Moonlight` and
`Swap R1/L1 <-> R2/L2`. All resource XML files now have a parsing check;
RCO compilation and native label appearance remain maintainer validation.

### 4.4 Textures

`_bg_texture` (`texture/bg.png`, page background). Add a texture by copying the file into
`cxml/texture/`, adding a `<texture src id type="texture/png">` entry, and rebuilding the RCO (`build_cxml.sh`).

Header separators use `_common_texture_ruled_line` from the already-loaded common PAF resource;
the former project PNG and `_header_line_texture` definition are removed **[code, 2026-10-23]**.
The maintainer-supplied `common_resource.rco` (SHA-256
`6ee58e58d1e78fecd99ea93e585c81efde3e940e3e0ca5cec4e64ba7cacdc806`)
defines this texture as a 328 x 4 GIM with `div_mode="3x1"`, `div_ratio_h="0.49"`.
Only rows 1/2 contain visible pixels; maximum alpha is 90/255 for black and 18/255 for white
**[code, extracted resource]**. Main/Search/Apps share a single 960 x 4 separator plane
in `template_top_title_bar`, centred at y = 96 (`anchor="0, 1"` inside the title plane),
targeting the visible dark/light pair at y = 95/96 without reducing the source height. These are layout
values, not proof of PAF filtering/division or final pixels. Rebuilt RCO/Vita appearance checks
remain **[open]**; the common RCO and extracted GIM/PNG are not bundled in the project.

`tex_pc` (`texture/pc.png`, 80 x 80 RGBA) is the original Sony Music PC-source icon,
extracted from the maintainer-supplied `musicbrowser_plugin.rco` and converted from GIM
to PNG with its original dimensions and transparency. It is bundled in this application's
RCO and drawn by the row's separate `plane_host_pc` / `plane_host_select_pc`;
loading the Music plugin is unnecessary. Main and Search share the ordinary template;
Main deletion uses the selection template **[code, 2026-10-23]**. A shared ImageButton
style owns only the background/glow, while CXML widget layout positions the icon.
The original `image_obj` placement failed in the supplied screenshot (see §5.2).
Build and Vita appearance/focus/touch validation of the corrected layout remain **[open]**.

`tex_add_pc` (`texture/tx_man.png`, **100 x 62 RGBA [code, 2026-10-24]**) is the
maintainer-supplied finished Add PC button artwork. Background, monitor and plus
are baked into this one image, as the camera is in Photos' button. The supplied
PNG is copied byte-for-byte; no redraw, crop, resize or conversion is applied.
File SHA-256:
`83fb42a9a4682f3d9c6bcaf3780410f90bbedefd22077caaa996c4d5c8896fb0`.
Its alpha >= **200/255** bounds are **[7, 8, 93, 54)**, preserving Photos' visible
**86 x 46** body inside the source canvas **[code, decoded pixels]**. This replaces
the former reconstructed blank background and separate Wi-Fi cross assets; both
unused PNGs and texture definitions are removed. `tex_pc` remains the PC-row icon.

### 4.5 Code helpers (`include/common.h`)

| Helper | Use |
|---|---|
| `bind_decide(root, id, cb, userdata)` | attach a decide (press) callback to a child by id |
| `set_widget_focusable(widget, on)` | make a widget non-focusable (checkboxes mirror state, the row owns focus) |
| `set_button_enabled(button, enabled)` | **the** way to disable a button: native `ButtonBase::Enable()/Disable()`, disabled colour `0.55, 0.55, 0.55`, and `SetActivate()` kept in sync **[hw]**. `SetActivate()` alone changes nothing visible; fading with `Widget::SetColor()` was rejected |
| `set_child_text(parent, id, text)` | set a child Text widget's string if it exists |
| `make_open_param` / `make_close_param` | page transition parameters |

### 4.6 System resources known to exist

Only these `_common_*` names appear in the XML and are known to resolve: `_common_default_style_box`,
`_common_default_style_button`, `_common_default_style_button_transparent`, `_common_default_style_check_box`,
`_common_sound_button_back`, `_common_sound_button_enter`, `_common_sound_image_button`,
`_common_style_corner_bottom_left`, `_common_style_corner_bottom_right`, `_common_style_plane_transparent`,
`_common_texture_list_70px`, `_common_texture_list_glow_70px`, `_common_texture_option_menu_base_down`,
`_common_texture_option_menu_button_{top,bottom,single}[_glow]`, `_common_texture_ruled_line`,
`_common_texture_button_glow` (hash `0x9b7bed4b` in the supplied common resource) **[code]**.

### 4.7 Lists (`paf::ui::ListView`) **[code]** unless tagged

- **Main startup regression, 2026-10-22:** use an empty PAF vector followed by resize for row
  storage. The installed ScePaf-RE sized constructor computes growth from an uninitialized
  capacity; the new count constructor in Main caused a null write consistent with the supplied
  core. It is replaced by empty construction/resize **[code]**. The maintainer's `6af2e3639c69`
  system-profile log reaches a one-PC Main refresh (after_delete=0/after_insert=1), two discovery
  cycles and four Apps cells without that crash **[hw, log; scoped]**. The captured Main refresh
  follows Settings; cold-start visibility/timing and >8-PC/selection remain **[open]**.
  InitialRefreshTask, list timing and CXML are unchanged.
  [Evidence and test-model limitation](MAIN_STARTUP_CRASH.md).
- Setup per page: `SetItemFactory(new ListViewFactory(this))`, `InsertSegment(0, 1)`, `SetCellSizeDefault(0, {960, 80})`,
  `SetSegmentLayoutType(0, LAYOUT_TYPE_LIST)`. The factory opens a template into `param.parent` and takes the last child
  as the item.
- Refresh: `DeleteCell(0, 0, existing)` then `InsertCell(0, 0, count)`. **The third argument of `DeleteCell` is a
  count, not the last index** **[hw on Main]**; `existing - 1` leaves a stale cell behind (a duplicate row). Search and
  Apps use the same call. Apps has logged 10-row population and a four-row → four-row rebuild
  with after_delete=0; full Search/shrink/empty acceptance remains open.
- Cells are created lazily by the factory; do not keep widget pointers across a refresh. Main/Search own
  dynamic `paf::vector<MoonlightHost>` snapshots **[code, 2026-10-21]**, removing their eight-host cap.
  `pages/host_list.h` queries the service count and copies that many records; discovery's total-count return
  can trigger a larger retry if more PCs arrive between count/copy. Discovery's existing 16-host backend
  limit remains. A failed read preserves old cells/data; an empty successful read clears the list. Old cells
  are deleted in full before swapping in new backing vectors. Main's initial-refresh task is unchanged.
  Apps owns a `paf::vector<MoonlightApplication>` sized from the
  `APPLICATIONS_READY` count, bounded by the backend's shared `MOONLIGHT_MAX_APPLICATIONS` (64), with no
  separate eight-row cap **[code, 2026-10-20]**. It deletes old cells before replacing data and inserts exactly
  the copied count. An empty ready result shows the empty state without calling `GetAll(NULL, 0)`, which would
  start another refresh. An invalid count/cache failure shows a load error.
- Apps buttons store the application ID in their PAF name. Their callback receives the page and resolves that ID
  in its current list, following BetterHomebrewBrowser's `EntryCB`/factory pattern. It holds no pointers into
  vector elements or a fixed callback-context array. Main/Search now use page userdata and per-refresh
  row tokens in widget names, following the same BHBB `EntryCB`/factory approach. Removed-cell tokens
  resolve to no current row; buttons/checkboxes keep no pointer into a resizable vector. Main stores
  dynamic per-row selection/checkbox state, remaps selection by UUID, then MAC, then address/port or
  addressless name, and rejects conflicting stronger identities. Search resolves its selected PC against
  the complete saved snapshot by address/port, with no duplicate-name fallback **[code]**. The existing
  native ListView scrolling remains; Apps now uses the 90 px Music-style row in §5.7.
- `[Apps] ShowApps count=... cells before=... after_delete=... after_insert=...` is emitted once per successful
  list population through the existing console debug toggle. Verify `after_delete=0`, `after_insert=count`,
  scrolling/selection and correct app ID at launch on Vita. A supplied 2026-10-20 log verifies
  `count=10`, `before=0`, `after_delete=0`, `after_insert=10`; the maintainer reports the requested >8 check OK
  **[hw, tested Vita; selection user-reported]**. The fragment does not identify a launched app. Smaller
  four-row → four-row rebuild is logged in the idle DisconnectHost test **[hw, log, 2026-10-21]**;
  shrinking/empty rebuild remains **[open]**. The 64/65-app boundary is unverified and explicitly deferred by
  the maintainer (2026-10-20), rather than required as the next test. Normal switching between PCs with different lists
  and return to the first is user-confirmed on 2026-10-20 **[hw, user-reported; no new log]**: each shows its own
  apps. The empty-list state is also user-confirmed on 2026-10-20 **[hw, user-reported; no new log]**:
  `No applications available.` appears without repeated requests or a hang. These checks do not validate
  concurrent host changes or every cache race. No agent build/hardware run.
- Selection mode rebuilds the cells and picks `template_host_list_item_select` instead of `template_host_list_item`.
  The checkbox exists only in the select template.
- Host-list source checks model 40 saved/16 discovered PCs, growth during reads, shrink/empty, read failure,
  identity-preserving selection, Select/Clear All, deletion after row eight and obsolete row tokens.
  All 117 Python non-build checks pass; the new nine checks interpret actual source with mocked vectors,
  widgets and services, not real PAF/allocator/thread behavior. Maintainer build and Vita scrolling,
  selection/Delete OK/Cancel, selection of a PC past eight and return navigation remain **[open]**.
  No CXML geometry/template, backend discovery limit, storage or protocol changes.

### 4.8 Status text

- Main/Search/Apps show static empty-list labels in the list area, independently of their permanent
  titles. Search's `text_search_status` uses the same 22 px centred style and y=220 placement as Apps;
  `ShowEmptyState()`/`HideStatus()` affect that label only **[code, 2026-10-23]**.
  Pairing keeps static instructions and the PIN. Progress/errors use native dialogs.
- On Main every return to idle goes through `Main::ShowIdleStatus()`: it shows the localized
  `msg_no_pcs` only with no hosts, outside selection/connection. The label would otherwise overlap
  the rows **[shot]**. Apps controls its empty state in `ShowApps()`.
- Main's `text_main_status` starts without a CXML label; `HideStatus()` also clears its string so
  parent/page transitions cannot expose stale empty-state text. Leaving selection mode refreshes
  hosts without an unconditional status `Show()` **[code, 2026-10-21]**.
  A failed host-store read preserves the current rows and hides the label rather than treating
  the error as an empty list **[code]**. Check startup with saved PCs,
  return from Search/Apps/Settings, selection Cancel/delete with PCs remaining, and a truly empty
  list on Vita **[open]**. No agent build or hardware test.

### 4.9 Events and threads **[code]**

Discovery lifecycle follow-up **[code, 2026-10-22]**: Search calls Start synchronously only to
start the backend-owned native scan worker. The extra PAF DiscoveryJob and stale service running
flag are removed. A start failure reaches the existing constructor's native OK dialog once;
the API does not also enqueue HOST_SCAN_FAILED for that synchronous error. HOST_SCAN_STARTED
marks a new attempt before worker startup; repeated Start during an active scan is a no-op.
Found/finished events still reach Search through MoonlightApp's main-thread queue. Stop always
reaps the backend worker (also after natural completion), and restart joins any old worker before
replacing its UID. No progress text/wait window, page navigation, scan duration or layout change.
All 126 non-build checks pass; real Search completion → Back/reopen, immediate Back/reopen,
single-error presentation and worker cleanup remain **[open]** for maintainer build/Vita testing.

Application event delivery now separates the latest HOSTS_CHANGED/SETTINGS_CHANGED snapshots
from a 16-slot ordered lifecycle FIFO **[code, 2026-10-21]**. Pairing/stream/closure and scan
boundaries/errors are never coalesced. A copied pending head remains stable while the foreground
service waits for its worker; it is acknowledged before the page callback. Producer updates do
not erase that head or a newer snapshot. The existing main-thread mutex/call list and native
dialog handoff are preserved. Snapshot bursts are source-tested; critical-only FIFO exhaustion
still logs rejection. Maintainer build/Vita smoke validation is **[open]**; no UI layout changes.

Stream presentation metadata carries a statistics-session token and queue timestamp with each
pending frame. The video bridge records queue replacement and successful PAF texture submission;
the statistics module rejects tokens from older sessions. These hooks measure CPU submission and
queue wait, not GPU completion or physical display. Source implementation only; build/hardware
validation is pending. Pages read snapshots through `MoonlightApp::Connection().GetStreamStats()`.

`PresentTask` is a persistent call-list entry registered once with the Stream instance and removed
in its destructor, like NetStream's surface update task. `QueueFrame()` only replaces the pending
frame; neither it nor the callback registers another entry. The deferred framebuffer release task
also stays registered while counting down and unregisters on completion or invalidation. PAF call
lists are persistent, so treating them as one-shot queues accumulated callbacks in the previous
source. The fix bounds registration count in source. Later owner-cleanup/restart and repeated
stream logs are scoped in the API audit; actual callback counts and attribution of the original
resource failure are not established by those traces.

Apps schedules the same generation-guarded deferred framebuffer release for STREAM_FAILED as
for STREAM_STOPPED **[code, 2026-10-21]**. Failed or cancelled setup can create decoder buffers
without publishing STARTED/opening Stream. Release remains on the main-thread call list after
common-c teardown; a pending release never frees a newer pool or a pool still referenced by an
active Stream page. This also covers a successful common-c return suppressed by a prior local
cancel, after the owner stops that transport. No new progress/error UI or inline text is added.
The later strict stage-4 cancellation trace verifies no first STARTED/Stream page, partial
common-c unwind → -7/CLOSED → native error termination → paired recovery/PASS late_start=0
and final normal stop/audio release/three unmaps **[hw, log, 2026-10-21]**. That first cancelled
setup never allocated video buffers. The earlier late_start=1 teardown test predates this change.
The existing startup test now offers stage 10 after video setup **[code, 2026-10-21]**:
it requires the old framebuffer generation to clear after FAILED/CLOSED before reconnect.
The later stage-10 trace verifies three mapped buffers/generation=1, suppressed frontend STARTED
after cancelled common-c success, owner cleanup → FAILED=-7/CLOSED → three old unmaps returning 0
before native error termination/reconnect, and same-app recovery/PASS **[hw, log, 2026-10-21]**.
Recovery decodes 445 frames; final double PS releases audio and all three buffers successfully.
The maintainer confirms image/sound on Sunshine 2025.924.154138. This covers that late cancelled-
success path on one Vita; other races, blocked-I/O latency, shutdown and repeats remain **[open]**.
See the [maintainer procedure and evidence](../tests/runtime/README.md#after-video-allocation-checkpoint).
No UI behavior is changed by this evidence record.

Three ordinary same-app start/double-PS stop cycles on system build 98f0d44194af now verify
Stream creation/infobar hide → owner stop=0/audio release → infobar restore/three successful
unmaps/deferred release before the next Start **[hw, log, 2026-10-21]**. Post-release USER_RW
free is 33596 KiB each time; newlib used rises by 464 bytes across the repeats, so this is
resource-reuse evidence rather than a leak-free proof. It does not validate host reconnect,
active application shutdown or the later ee485a2 Main-label change. See
[the recorded result](../tests/runtime/README.md#ordinary-repeated-startstop--maintainer-result-2026-10-21).

Backend callbacks may arrive on worker threads. `MoonlightApp` queues them and delivers them through
`MainThreadCallList`, so page callbacks run on the PAF main thread. Only the topmost page owns the event callback; when
a page is destroyed it hands the callback back to the page below (`RestoreEventCallback()` in `Main`, `Search`, `Apps`,
`Pairing`). Streaming stays behind the `moonlight_api_*` boundary; never move it into a page.

### 4.10 Controller RGB overlay **[code, 2026-10-22; Vita validation open]**

Input settings now offer `Controller light`: Off (default), Like DualShock 4, Like DualSense.
The choice is captured on the next stream; it changes the local effect, not the host controller
type. This is game/controller RGB feedback, not an image-derived ambient-light effect. A host
virtual controller/game must produce RGB output; no default blue or invented color is displayed.
The existing common-c `setControllerLED` callback receives controller 0 RGB. Input advertises
`LI_CCAP_RGB_LED` only for an enabled, started session. No protocol/dependency replacement or
physical Vita/controller LED API is introduced.

The stream mutex protects a small cached snapshot (generation, mode, RGB). The callback writes
only that cache, ignoring other controller IDs, Off and stopping/finished sessions. An accepted
start resets RGB to black and advances the generation; the sole owner joins transport callbacks
before another session can be admitted. The getter reports Off before STARTED and immediately
after stop/cancel/termination or completion. There is no new event type, worker, allocation,
network query, per-frame diagnostic or statistics dependency.

`ConnectionService -> backend -> Moonlight API -> stream` exposes the snapshot. Stream's existing
main-thread `PresentTask` reads it even when no video frame arrives, rejects another generation
and changes PAF widgets only when mode/RGB changes. Off pages do not poll it. Black hides the
effect, including its halo. The planes belong to the Stream root and disappear with that page;
no additional call-list registration or framebuffer ownership is added. Video scaling/cropping,
statistics, touch/controller input and infobar behavior are unchanged.

Appearance is project artwork, **not measured Sony UI or hardware-verified geometry**:

- Like DualShock 4: a **200 x 36 px [code]** white/alpha mask anchored at bottom center. Its
  light-bar lens has an almost straight bottom, rounded ends and a raised curved upper center,
  with a soft halo. Host RGB tints it. The silhouette follows the maintainer's DS4 photo:
  blue lens bounds **x=348..833, y=493..571 [shot]**, about **6.2:1 [shot]** width/height;
  the source lens spans approximately **164 x 26 px [code]** inside the existing plane.
  Per the 2026-10-23 request, the mask is rotated **180 degrees [code]** from the photo's
  orientation so the straight edge faces the screen bottom; Vita viewing remains **[open]**.
- Like DualSense: two **24 x 448 px [code]** planes flush to the left/right edges, vertically
  centered. Mirrored **16 x 128 px [code]** alpha masks fade inward and toward both ends.
- All three planes appear after video and before statistics in CXML. Both style and planeobj
  colors remain white; widget tint supplies RGB. No full-screen tint, top/bottom border, animation
  loop or input handler is added. Source masks total **45,184 uncompressed RGBA bytes [code]**;
  this is not a measurement of PAF/GPU allocation overhead.

`tools/generate_controller_light_textures.py` authors these source PNG masks with the standard
library; it does not compile resources. Ten non-build checks interpret the actual RGB callback,
accepted-start reset, snapshot getter and normalized PAF update method with serial mutex/widget
mocks. They cover filtering, stop/cancel/inactive gating, restart, black, duplicate events, stale
generation, Off/missing-widget behavior, service/capability wiring, CXML layering/localization and
reproducible alpha assets. A software composition preview checks source artwork only. CXML/C++
compilation, real callback ordering, PAF alpha/tint, AppSettings persistence and both modes over
video (including stop/restart, paused frames, crop/fit, statistics and Quick Actions) remain
**[open]** for the maintainer's build/Vita validation. No agent build or device run.

**Maintainer follow-up, 2026-10-22:** the user reports both modes work **[hw, user-reported]**
and supplies `2026-10-22-154233.jpg` showing the prior orange DS4 cap over a running stream
**[shot]**. This establishes the reported basic RGB/display path, not the entire lifetime,
settings-persistence or performance matrix above. The DS4-only source mask is now reshaped to
match the supplied real light-bar photo (`codex-clipboard-7de963d3-463a-4830-a94e-38bdd7a2016e.png`);
its plane size/anchor and DualSense assets are unchanged. Software preview and existing mask
checks verify source artwork; the revised shape still needs maintainer RCO rebuild/Vita viewing
**[open]**. No agent build or device run.

## 5. Components and their measured look

### 5.1 Header and paragraph

The supplied official Settings resources and ELF are now traced in
[Settings UI research](SETTINGS_UI_RESEARCH.md) **[code, 2026-10-23]**. Its shared
header uses a transparent 960 x 64 plane, a centred horizontal box with 32 px bold
text, and a **local 960 x 2 separator** (`ID hash 0x69cb3790`), rather than
`_common_texture_ruled_line`. Following the maintainer's request, Main/Search/Apps
now share that plane/box/text composition with the common-resource separator instead
of Sony's local texture **[code, 2026-10-23]**. The same research confirms that the Wi-Fi sphere is a connection
indicator (animated green while connecting, steady green when connected, dim
otherwise), not a reachability indicator for every listed AP.

`template_top_title_bar` keeps the transparent 960 x 64 plane in y=32..96. Its
centred horizontal `box_top_title` has `adjust="2, 2"`, zero spacing and a 760 px
text slot (`align="0, 4"`, `adjust="0, 2"`), matching the decoded Settings layout.
`style_text_header` binds a 32 px bold white text object with centred X/Y and ellipsis;
the former title auto-scroll is removed. Main retains `Connect to a PC`, Apps retains
`Applications`, and Search sets localized `msg_search_pcs` once in its constructor.
Search no longer hides its title when hosts appear; only its separate empty-list
label is hidden. Existing corner-button navigation and list geometry remain.
Pairing's PS4 Link flow layout and Stream's full-screen video retain no standard
header. Native AppSettings owns its own header. These are source changes; CXML/C++
build, PAF box/text layout, clipping and rendered separator alignment need maintainer
Vita validation **[open]**. No agent build or hardware test.

| Item | Value | Source |
|---|---|---|
| Shared Main/Search/Apps header (`style_text_header`) | 32 px bold white, centred in a 760 px text slot within a horizontal box | decoded Settings resources and current CXML **[code]**; Vita appearance **[open]** |
| Earlier flow/list header references | 26 px regular, text origin x = 64 / 80, cap centre y = 61.5 | PS4 Link search / "Which feature..." **[shot]**; superseded for the shared header |
| Header separator | system `_common_texture_ruled_line`, 960 x 4 plane targeting visible rows y = 95/96 | source geometry **[code, 2026-10-23]**; Vita appearance **[open]** |
| Paragraph (`style_text_paragraph`) | 26 px, line pitch 40, x = 64, first line centre y = 108, wrap width about 790 | PS4 Link pairing page **[shot]** |

The PS4 Link reference has a dark/light pair at y = 95/96 **[shot]**. The shared
Main/Search/Apps title bar explicitly draws the native separator at that boundary **[code]**;
the first list row can also contribute its own edge. Final combined appearance needs a Vita check.

#### Main manual-entry header button — 2026-10-23

The Photos camera button in `2026-10-09-193740.jpg` occupies approximately
**x=9..95, y=41..87 [shot]**, centred at **(52, 64) [shot]**. The subsequently
supplied `photocam_plugin.rco` (SHA-256
`b754d14074a0244b0c51fc550cf8e78205647c44b89d2914d3d9787ceff9e3c5`)
confirms the actual layout: templates `0x3040266a` / `0x6fe191e2` contain button
`0x4a5c79cd` with **100 x 62**, `anchor="1, 2"`, `pos="52, -64"`, and a
**88 x 48** focus frame, shape **0 [code, decoded resource]**. Its local style
`0x802ab201` uses a background object and native `_common_texture_button_glow`
with scale modes **2/2**, scale value **86 x 46**, blend **2 [code]**.
The camera/play glyph is baked into Photos' local background textures. Moonlight
now uses the maintainer's finished `tx_man.png` with PC-plus artwork baked into its
background in the same way (see §4.4, updated 2026-10-24).

The background's **100 x 62** source canvas must not be confused with its visible
body. Both the original Photos camera texture and the supplied `tex_add_pc` have
alpha >= **200/255** bounds **[7, 8, 93, 54)**, i.e. **86 x 46 [code, decoded pixels]**.
At the resource's unscaled layout position, the canvas starts at screen **(2, 33)**;
its solid body therefore occupies **[9, 41, 95, 87) [code]**, matching the screenshot
measurement above **[shot]**. Lower-alpha shadow extends beyond that rectangle.
Reducing the whole widget to **86 x 46** also reduced this body to about **74 x 34**;
that was the cause of the maintainer's subsequent too-small report. The earlier
standard PAF background was a different texture and did not establish Photos sizing.

Main now matches the decoded Photos button geometry: **100 x 62** canvas centred at
**(52, 64)**, **88 x 48** focus frame (shape **0**), and **86 x 46** glow with scale
modes **2/2**, blend **2 [code]**. `btn_add_pc` binds `tex_add_pc` through
its `texture` attribute; `style_button_header_action` leaves its background planeobj
empty, exactly as Photos does. This replaces the previous style-level texture
assignment. The supplied texture's alpha-body bounds, position and these layout/style
parameters are source-compared; final PAF rendering is still **[open]**. The reference screenshot
is in selection mode and the camera appears dimmed **[shot]**; this change follows
the resource's white **1, 1, 1, 1 [code]** normal button color. State-dependent
runtime dimming has not been measured.

The supplied texture replaces the separate PC/cross child planes. No overlay,
rotation or icon-specific sizing remains; the native button owns the complete
artwork, touch, focus and the existing decide callback **[code, 2026-10-24]**.
The icon has no text label. The previous bottom-wide button/box and unused prompt
string are removed. Main's title and host-list/selection-bar geometry stay unchanged.

`btn_add_pc` still opens the existing native Vita IME. In Delete selection mode,
the button and its container remain visible; `set_button_enabled()` disables the
button on entry and enables it on exit **[code, 2026-10-24]**. `OpenAddPc()` also
rejects activation during selection. Existing discovery pause/resume is unchanged.
Resource/XML source checks pass. The maintainer accepts Add PC and current checkbox/Delete
behavior **[hw, user-reported, 2026-10-27]**. No agent build or hardware test.

### 5.2 List rows (PS4 Link "Which feature...") **[shot]**

**Historical PS4 Link layout below:** Main now follows the Music top-row geometry
and typography in §5.7 (2026-10-30); the right-side PC icon/text/dot coordinates
below describe the earlier implementation, not current Main. The selection bar
and native selection actions retain their existing behavior.

Title 28 px regular, cap centre 25 px below the row top; description 22 px at 85% white, cap centre 58.5 px below the
row top. PS4 Link text starts at x = 220 because of its icon column. Main/Search PC rows
use the Music `tex_pc` icon in an 80 x 80 sibling `plane` at the right of both
normal and selection rows, as requested by the maintainer: `anchor="2, 0"`,
`align="2, 0"`, `pos="-80, 0"` **[code, 2026-10-23]**. Its right edge is x=880,
centre x=840 and left edge x=800, leaving 20 px inside the button's x=900 edge.
Title/address stop at x=780 to leave a 20 px gap before the icon. This placement
is a requested source-layout change; its rendered appearance remains **[open]**.

The maintainer's `2026-10-23-023359.jpg` shows the original icon centred at screen
x≈480 and overlapping PC names **[shot]**. The original ImageButton `image_obj`
`planeobj pos="-360, 0"` / `"-280, 0"` did not produce its intended position in
that run. The correction uses widget layout for the icon, alongside the row's text
and availability plane, avoiding ImageButton's internal image positioning.
Both modes share the background/glow style; button ids, focus and selection callbacks
are unchanged. Corrected appearance and touch/focus still require a rebuilt RCO/Vita
check **[open]**; the supplied shot does not validate the correction.

Main/Search PC rows now reuse the official Wi-Fi green/dim sphere artwork as a
27×27 noninteractive plane **[code, trial implementation 2026-10-23; not hw]**.
Normal rows: dot centre x=178, title/address x=208, width 572; selection rows add
80 px to the dot/text start (dot x=258, text x=288, width 492). Both text blocks end
at x=780; the PC icon occupies the same right-hand slot in either mode, and the
checkbox remains on the left. Apps rows do not have this indicator. PNGs are byte-preserving
30×30 exports of `wifi_settings_plugin.rco` texture IDs `fbd879ae` (green) and
`9718c305` (dim), displayed smaller by CXML.

Green means the configured `internal` IPv4/hostname + GameStream port accepted TCP
within the last 30 seconds. It does not authenticate Sunshine or establish pairing,
app idleness or streaming readiness. Dim means no fresh confirmation, including
unchecked, failed, cancelled and expired results; it does not establish power-off.
The stored/discovered `online` field is not used. Results stay in memory only.

`HostService` owns one dedicated single-worker PAF job queue. Active Main/Search
request a scan on entry/return or a changed UUID/address/port snapshot. While the
list remains active, unchanged snapshots are checked again after 15 seconds from
the previous scan's start, and only after that scan finishes **[code, 2026-10-23]**.
The fresh previous positive remains visible while its replacement is pending,
using its original timestamp and 30-second expiry; a new negative result turns it
dim immediately. Long scans run serially, so an observation can still expire if
its next check cannot finish within 30 seconds. Page call-list tasks only manage
scan ownership; hidden lists, dialogs, Settings and streaming do not schedule repeats.
The maintainer reported Main's dot becoming dim over time in the initial trial;
source confirmed expiry without a repeat scan. This refresh correction still
needs maintainer build/Vita validation.
`MoonlightApp::ProcessEventTask` collects observations/expiry and delivers a
coalesced `HOST_AVAILABILITY_CHANGED` snapshot event. Factories initialize new
cells; event handlers change textures on generated cells without rebuilding the
list or replacing row tokens. Focus, scrolling and selection are preserved by design.

Leaving/hiding the list, IME, Delete confirmation, Settings and foreground busy
cancel the owned scan. Foreground admission cancels any probe; Connect's existing
worker waits for the last successfully queued scan before touching GameStream.
The single-worker FIFO also drains older cancelled scans; failed submissions do
not replace that barrier. Ordinary cancellation never joins on the PAF thread.
Application teardown drains/deletes this queue before backend/network shutdown.

`legacy_host_probe.c` uses an isolated nonblocking socket, a one-second monotonic
connect budget and 10 ms cancellation polling. Numeric IPv4 bypasses DNS; native
resolver timeout/retry parameters are 1/1, with cancellation checked on return
(the native DNS call itself is not interrupted). No HTTP, credentials, server
selection or curl/crypto initialization occurs. DNS timing/cancellation latency,
PAF queue operation, scrolling texture changes and actual layout still require a
maintainer build/Vita run. Source mocks do not verify native timing or ABI.
See the [assessment and trial notes](SETTINGS_UI_RESEARCH.md#trial-implementation)
for the design limits and acceptance cases.

### 5.3 Bottom bars

| Bar | Look | Source |
|---|---|---|
| Selection bar (Photos) | 64 px, top at y = 480; body about 5% darker than the page; dark row y = 480 (5% black extra), light row y = 481 (18% white) | system Photos **[shot]** |
| Earlier flow-bar reference (PS4 Link) | 64 px, opaque; body (14, 27, 119) from y = 480; edge rows (6, 21, 108) at 480, (83, 94, 173) at 481, (42, 53, 135) at 482 | PS4 Link **[shot]**, identical on three different pages; palette superseded for Pairing on 2026-10-28 (§2.3) |

The selection bar keeps the Photos values on purpose. A stronger tint (12% / 10% / 30%) was tried on the blue theme
and judged too prominent.

Bar buttons **[shot]**: 144 x 45 px visible, `adjust="2, 0, 0"` with `size="0, 46, 0"`. Left button `pos="9, 9"`. The
right group (Select All / Delete) is a horizontal `box` anchored right with `pos="-8, 9"` and `space="9"`; the visible
gap is about 12.5 px and the right edge about 10 px from the screen edge. Do not pre-fit widths: labels change
(Select All becomes "Clear All" only when every saved PC is selected, `Main::AllHostsSelected()`). Widths and
positions matched Photos to within 1 px on a screenshot; resizing when the label changes has not been confirmed
separately (**[open]**).

### 5.4 Popup (`OptionMenu`, speech balloon)

- A real vertical PAF `<speech_balloon>` in `page_settings_bubble`, texture `_common_texture_option_menu_base_down`
  (tail points at the bottom-right corner button). Actions: Delete on top (`style_button_option_top`), Settings at the
  bottom (`style_button_option_bottom`). This is a project-owned composition styled from system apps, not a discovered
  Sony action-menu API. Placement, Delete/Settings focus and the disabled Delete look are **[hw]**.
- Size: 202 x 60 px buttons, 6 px margins, so height = 60 x buttons + 12; width 214.
- Position (`option_menu.cpp`): `SetPos()` centre at x = 258 (the balloon spans x 631 - 845) and a vertical centre
  derived from the button count so the bottom edge stays 50 px above the screen bottom. The old trial
  `SetPos(420, -140)` put the balloon partly off screen; do not bring it back.
- Historical hardware observation: an earlier test of Sony `_common_template_speech_balloon_menu_3` (`0x4a34c804`)
  gave a centred horizontal menu with `SetAdjust(0, 0, 0)` and `SetPosCenter(paf::math::v4(0, 0, 0))`; `(480, 272)`
  moved it upper-right. It confirmed centre-origin coordinates for that horizontal template only. Do not apply its
  `SetPosCenter()` setup to this vertical popup, which uses `SetPos()`.
- The official `Princess-of-Sleeping/vitasdk-paf-component` sample wraps a vertical `box` with 7 px margins and
  top/middle/bottom system option-menu buttons (glow textures, `_common_sound_button_enter`) in a
  `<speech_balloon texture="_common_texture_option_menu_base_side">`. The production popup uses
  `_common_texture_option_menu_base_down` instead so the tail points toward the `...` button; it needs only the top
  and bottom button styles, the middle one is no longer needed.

### 5.5 Selection mode on Main

Popup -> Delete -> multi-selection: every row shows a checkbox (`checkbox_host_select`, 58 x 58 at `pos="92, 0"`)
that mirrors the row. The checkbox retains its position; the PC image slot spans row x = 160-240,
followed by text at x = 255 **[code, 2026-10-23; Vita validation open]**.
Activating the row toggles it; the bottom selection bar offers Cancel, Select
All / Clear all and Delete; Delete is disabled until something is selected and asks for confirmation through
`SceMessageDialog`. There is no Copy or clipboard action and no `SceClipboard` dependency; do not restore it unless
asked.

**Checkmark regression, 2026-10-24 [code]:** the factory renames row buttons and checkboxes
to callback tokens. The incremental list update incorrectly still searched for
`checkbox_host_select`, so selection changed in the model without reaching the live
checkbox's `SetCheck()`. `UpdateHostItem()` now looks up `checkbox_token`; focus capture
likewise looks up the row's `token` instead of its old button template ID. Factory lookups
before renaming remain valid. Native CheckBox/style, events, deletion confirmation and
selection persistence are unchanged; no widget pointers are retained across virtualization.

Two non-build regression checks first fail against the previous source, then pass with the
fix. They interpret actual row/Select All toggles, item updates and focus capture using
strict token-only widget mocks, including a list of 12 PCs and a missing/recreated item.
These establish source lookup/state behavior, not native PAF drawing or ABI. The maintainer
accepts current checkboxes, Select/Clear All and Delete **[hw, user-reported, 2026-10-27]**;
no agent build or hardware run.

### 5.6 Photos folded-parent navigation — 2026-10-28

The [Photos binary investigation](PHOTOS_NAVIGATION_RESEARCH.md) recovers a local
`furl_stack` using native PAF position/quaternion/meta-alpha animation **[code]**.
The screenshot shows the previous category list at the left **[shot]**; the
maintainer confirms the basic animation works on Vita and initially reports
title overlap at the end of Back. After correction `2b36285`, the maintainer
replies “вроде всё ок” **[hw, tentative user-reported, 2026-10-28]**. This supports
ordinary transition/title-return appearance; no profile, package hash or runtime
log was supplied, and the separate cases below were not individually reported.

- Main's `plane_main_content` contains its existing chrome/host list, with its
  background outside. Apps' `plane_apps_content` contains its title bar and
  list/empty state; its Back corner remains outside. Apps no longer draws an
  opaque background.
- Both containers are 960 × 544, left-aligned at `(-480, 0)` in center-origin
  PAF coordinates **[code]**. This expresses the left pivot in CXML. Main's
  folded target is `(-596, 0, -150)`, Y rotation `+π/2`, meta-alpha `0.15`.
  Apps enters from `(480, 0, 330)`, Y rotation `−π/2`, alpha `0`, then returns
  to the CXML foreground transform. Geometry uses 500 ms `FUNC_CIRQ_OUT` timers;
  alpha uses 400 ms linear timers. These targets follow Photos' recovered
  defaults; perspective and actual strip width remain **[open]**.
- The initial prototype made Apps' list/cell/button 730 px wide to follow
  the Photos grid x=115…845 reference. This was superseded by Music's independent
  840 px backdrop / 900 px focus in §5.7. Current cells are 960×90; Main cells
  remain 960×80. The retained-parent navigation/row identity logic is unchanged.
- Apps owns both animations and uses two native completion callbacks. A PAF
  main-thread task reopens input only after both complete; Back animates the
  reverse targets and deletes Apps from that task, outside the native callback.
  No sleeps, per-frame transform updates, image snapshots or second stack.
- `Base` keeps a transitioning current page deactivated when a non-current PIN
  page is removed. LiveArea admission rejects a transition; a requested app ID
  waits for both successful list readiness and entrance completion. Forced Apps
  deletion cancels the owned callbacks/task and restores Main before activation.
  Timer allocation/API failure cancels animations and applies final targets so
  input can resume. Missing containers log and retain immediate navigation for
  an older resource. Stream, PIN, Settings and OptionMenu transitions retain
  their existing behavior. Discovery remains paused while Apps is current.

**Return-title correction [code, 2026-10-28]:** Apps' title template originally
sat outside its animated content. It remained visible until page deletion while
Main's title returned to the same screen position, producing the reported late
overlap. The title template (including its separator) now belongs to
`plane_apps_content`, so it shares the existing 400 ms fade and 500 ms movement.
The resource regression assertion fails before this move and passes afterward;
no new animation timers, callbacks or visibility state are needed. Corrected
native title appearance has the tentative maintainer acceptance recorded above;
do not reopen this basic check without a regression.

Five non-build checks interpret the actual Apps helper/state/callback/cleanup
bodies with serial PAF mocks; existing LiveArea admission checks include the
transition gate. XML/reference checks also pass. They do not establish native
API ownership, ABI, projection/clipping, focus/scroll preservation or rendering.
The basic transition/title-return has tentative maintainer Vita evidence above.
PIN → Apps → Back, early LiveArea app readiness, empty/error lists, repeated
entry/Back, focus/scroll retention and Stream → Apps → Main remain **[open]**;
these cases were not individually reported. No agent build or hardware run.

### 5.7 Music-style application artwork — 2026-10-30

For measured differences from Music/Photos, see the
[screen comparison](MUSIC_PHOTOS_UI_COMPARISON.md). That report separates
resource dimensions from screenshot measurements and unresolved screen mappings.

**[code; build and Vita appearance open]** Apps uses a dedicated native ListView
row based on the maintainer's official Music application reference. The existing
Moonlight background, title, Back corner and Photos-style folded-parent navigation
remain. An application has one vertically centred 28 px bold title, with native
ellipsis/long-press text scrolling; no artist or synthetic second-line metadata is
invented. Application names remain server text; existing EN/RU application/empty/error
strings are reused without adding dictionary keys.

Reference evidence, inspected read-only without compilation:

- `musicbrowser_plugin.rco` SHA256
  `f5a84d00c75e5e443a55468a3f37e3d8de0f9875d0248a2d93d49a22226d0bf2`.
  The CXML tables contain 650 nodes. Album template `ac52b58e`, node `0x1044`,
  has a 90 px row, a 90×90 child cover at `0x1248`, and focus shape 3
  with 900×90 focus bounds **[code]**. The image-button style `eb731fb1`
  uses 92×92 image geometry; the visible square slot is 90×90. Its row backdrop
  has meta-alpha 0.6. The generic 32 px text style is not the runtime row
  label; see the ELF typography recovery below.
- ELF `SceMusicBrowser`, SHA256
  `618aa1b0d828cd620f922debb979512cc7175dde639e5b9f08cf09061bb56392`.
  Import NIDs resolve through the installed PAF database. Calls at `0x81098308`
  and `0x8109834c` use native ListView factories/cell sizing. The image path at
  `0x810ad0a0` calls `Surface::Load` on a memory buffer **[code]**. This is
  evidence of the native image/list path, not execution or a recovered public
  Music browser API. Moonlight uses the installed typed PAF surface loader.
- Screenshot `2026-10-29-220904.jpg`, SHA256
  `2b20049e3f9f9b6f5bcd9cc2eeac666496678fc51e661cfb43f55c4efc0b7187`:
  cover strip approximately x=147…237, row boundaries y=96,186,276,366,456,
  title starts around x=252 **[shot]**. The initial 730 px adaptation is now
  replaced: a 960 px viewport/cell at x=7 gives row centre x=487. The native
  cover offset −295 gives centre x=192; button left margin 245 gives text x=252
  and a nominal 15 px gap. The 7 px viewport offset is screenshot-derived,
  not a recovered native viewport constant; clipping/scrollbar need Vita review.
- `texture/music_row.png` and `music_row_glow.png` are lossless RGBA exports
  of Music texture IDs `5b971d4f` and `c0176b51`: 680×92 pixels each **[code]**.
  CXML scales them to the native 840×90, with 900×90 focus bounds,
  preserving the original backdrop alpha and additive-focus treatment. The existing packaged app icon is reused
  as a 64×64 fallback. See [asset provenance](LICENSING.md).

Music layout correction (2026-10-30), **[code; native appearance open]**:

- Main uses `filelist_template_music_top` (`a2bf3870`, RCO node `0x19d8`)
  as its row reference: 80 px height, 840 px backdrop, 900 px focus and
  80 px icon at −300 relative to row centre. Hashing the embedded ELF strings
  at `0x810da1a8` / `0x810db0c8` identifies that template; the 90 px group and
  track templates are `adcafa27` / `ac52b58e` (`0x810d94b8` / `0x810d96dc`).
- The ELF label helper `0x8107671e` loads Point 28 at `0x8107676c` and marks
  primary modes 1/2/3/5/7/8 bold (`0x810767ae`, `0x810767d0`, final Bold
  attribute 7 call at `0x8107708a`). Secondary modes 4/6/9 use Point 20 and
  do not set bold (`0x810767c0`, `0x810767f2`). `default_label` is passed mode 1
  at `0x8107f678…0x8107f690`; two-line filelist labels use upper/lower modes
  8/9 at `0x81067a86…0x81067b22`. Text construction receives the selected point
  value at `0x810768b8` / `0x81076e34`. These are code facts from the supplied
  binary, not claims of a device run. Main/Apps now use 28 bold; Main's address
  uses 20 regular at its existing 85% white. Header text stays 32 bold.
- Main's PC icon is now on the left: x=147…227, with title/address at x=252…900.
  The existing two-line host content is an adaptation, not a new claim that Music
  top categories contain addresses. Saved and discovered rows share columns;
  availability is a 27 px badge centred at x=159, 25 px below the row centre.
  Selection keeps those columns, with the 58 px checkbox at x=64…122; it does
  not overlap the icon. Row tokens, selection callbacks and the bottom bar remain.
- Main backdrop/glow use native Music IDs `6b5a7f8a` / `be12fb16`, losslessly
  exported to `music_top_row{,_glow}.png` (680×72) and scaled to 840×80.
  The GIM decoder was checked byte-for-byte against the existing album PNG.
  Apps retains its separate native album textures, square 90 px slot and
  aspect-preserving portrait thumbnails; portrait art still has extra side space.
- The two new resident Main textures are included in the conservative pool
  model (704×128×4 bytes each). Artwork cache capacity is now six, sufficient
  for the zero-margin 448 px viewport's generated rows, so the 8 MiB pool still
  covers the bounded 1024×1024 source preflight. A full six-entry padded cache
  plus the added texture allowance leaves 4,303,864 bytes in that arithmetic
  model versus 4,259,840 required. Native fragmentation and actual allocation
  remain unverified; larger lists may refetch evicted off-screen covers.
- No user-facing strings change; all EN/RU IDs and existing service boundaries
  remain. Resource/localization checks and the 305 Python checks pass. Maintainer
  gate: rebuild RCO/application; check Main normal/Delete and Apps, Russian/English
  names, long names, scrollbar/folded strip, and artwork/stream memory on Vita.

ApplicationService owns a single-worker 256 KiB PAF queue and one cancellable
image job. The maintainer's first artwork build stopped at direct access to
private `Framework::surface_pool` / `decode_heap` members. The source correction
used the installed public pool/heap accessors. The crash correction below retains
`gutil::GetDefaultSurfacePool()` and lets `Surface::Load` choose its default decoder
heap; the global heap is no longer substituted for the private framework decode
heap. No framework layout access or new allocator is introduced.
The job fetches the current paired server's `/appasset` with the ordinary
client identity and complete server-certificate pin; no plaintext fallback or
administrative API is added. The host-control admission guard excludes other
session requests. Only IDs in the current valid application list are accepted.
The existing HTTP transfer gains an optional response bound; XML requests retain
their existing policy. Artwork has a 512 KiB response limit and a five-second
transfer timeout, with overflow-safe writes and a job-owned cancellation token.

Visibility correction/diagnostics (2026-10-30): the maintainer initially reported
names without icons, then corrected this to white squares. After the resource fix,
the maintainer confirms visible Moonlight fallback icons; actual covers still fail.
The image planes now belong directly to ListItem, following Main's working PC-icon
composition, outside ImageButton's label-margin layout. The cover plane starts with
an explicit packaged texture so its drawable is initialized, is hidden by the row
factory, and is shown only after successful SetTexture. Failed binding preserves
the fallback; cleanup hides and detaches the cover before stream allocation.
Fallback visibility is now maintainer-observed; successful cover binding remains
open. A serial source check covers failed/successful binding and fallback order, and a resource check requires sibling, initialized planes.

Debug-log-only `[Artwork]` records now identify row creation, page gate/generation
changes, enqueue/fetch, response bytes/PNG dimensions, decoder phase/result, and
native texture binding. Page messages are deduplicated by gate/generated-row state;
no per-frame/chunk/file logging is added. Gate bits: 1 list not ready, 2 missing list,
4 transition, 8 launching, 16 inactive page, 32 foreground busy, 64 pending action.
Current decode phases: 0 before native loading (including insufficient pool space),
1 at Surface::Load, 2 at validated native dimensions/layout, 3 after pixel reduction,
4 at thumbnail allocation/Copy. A `loaded` event records native error, dimensions,
stride and GXM format; a `memory` event records pool free/required bytes.
Actual allocation/decode/binding remain native gates.

Crash correction (2026-10-30): the supplied log fetched valid-sized PNGs, failed the
first at the old Resize phase, then crashed after fetching the second. The cancelled,
truncated core `psp2core-1793317355-0x00003144ff-eboot.bin.psp2dmp.tmp` (SHA256
`58c620b34cc517649ae174c6bd7e43755b8ae02b3caa4684dc5f70fef34f476a`)
retains the faulting `Application artwork` thread: PC `0xe0259632` in ScePaf,
module offset `0x4f932`. Its application return address `0x81080b9f` maps to the
current ELF's return after `Surface::DecodeImage` at `0x81009b9a`. The worker SP
is within its 256 KiB stack, near the top; this does not indicate stack exhaustion.
The core is incomplete and does not prove a particular internal PAF assertion or
allocator fault. Raw core memory is not committed.

The job now uses the public memory-buffer `Surface::Load` entry point with default
heap/setup, as observed in Music and the installed PAF image-to-texture sample;
it no longer independently opens/resizes Image or calls DecodeImage. Linear RGBA/
BGRA pixels are validated against native dimensions, stride and page size, reduced
by bounded rectangle averaging into at most 90×90 pixels, then copied through
PAF into a small native surface. This avoids passing a lazy resize operation into
the internal decoder. Its initial twelve-entry cache was reduced to six by the Music layout correction above. The temporary
full-size native surface is released before thumbnail allocation; no full-size
surface enters the cache. Pool admission requires conservatively padded source
storage plus 64 KiB overhead. This is a free-space preflight, not an atomic pool
reservation or a guarantee against fragmentation; loader/allocator errors retain
the fallback. Insufficient memory or unsupported native pixel layouts also retain
it. Transient decoder allocation/latency and this crash correction require the
maintainer's application rebuild/Vita retest; the agent did not build or run PAF.

Pool headroom correction (2026-10-30): the maintainer reports no further crash,
but every job still stops at phase 0, **before Surface::Load**. The log reports
1,223,672 free bytes against 1,687,552 required for 528×704 and 2,195,456 for
600×800; the PNG requests succeeded. This does not yet exercise the replacement
native decoder. The system surface pool is now 8 MiB instead of 4 MiB; the
1 MiB text pool, 10 MiB PAF global heap, 6 MiB newlib capacity and default 64 MiB
SELF budget remain. At the captured UI occupancy, the additional 4 MiB covers the
preflight for a maximum 1024×1024 source even with the then-twelve conservatively padded
thumbnails. A non-build regression calculation fails for the old capacity and
passes for the new one. This is capacity arithmetic, not native allocator or
fragmentation validation; source/thumbnail allocation errors still preserve the
fallback. The larger surface reservation persists while the framework runs.
Maintainer gate: rebuild the application, open the same Apps and check actual
`loaded/complete/bind` results, then verify startup with a retained Vita game and
stream start/stop/return under the larger pool. Those native paths remain **[open]**.

Native image ABI correction (2026-10-30): after increasing the pool, the full core
`psp2core-1793318590-0x00007231bb-eboot.bin.psp2dmp` (SHA256
`09ceeff5734abd57d62d496a8639812cfdfd5ac3cdd00b2946d91874f0122121`)
records `Application artwork` at PAF `abort+0x12` (`0xe0259632`). Its exported
LIBRARY_INFO NID/address pairs identify HeapAllocator::sce_paf_memalign,
SurfacePool::Allocate, Surface::Initialize/constructor and DecodeImage/Load in the
stack. The allocation request is `0x4075c580` bytes (about 1 GiB), with invalid
surface dimensions despite the 528×704 PNG header. Application return
`0x81010b99` maps to ELF `0x81009b98`, directly after Surface::Load.

The caller ELF has `Tag_ABI_enum_size: small`; its constructor stores the option
resize enum one byte after flag 0x68, instead of at 0x6c. The supplied Music ELF's
constructor at `0x8108cf4a…0x8108cfc8` places the option at object +0x48 and writes
32-bit resize_type at +0xb4 (option +0x6c), image_order at +0xcc (+0x84), and the
last flag at +0xdc (+0x94); its copy at `0x8108cff6` copies 0x95 payload bytes.
Thus the native option occupies 0x98 bytes with alignment, while the current SDK
header compiled with short enums occupies 0x90 and shifts fields after 0x68.
This mismatch also shifts inline Surface stride/page-size fields and the size
used by client `new Surface`. More pool memory cannot correct that ABI.

Only `src/services/application_service.cpp` now compiles with `-fno-short-enums`.
Its native LoadOption, inline Surface access and allocation use 32-bit enums;
compile-time assertions require the observed option size/offsets and ImageMode/
ImageOrder widths. Its cross-file service boundary uses pointers/references,
integer application IDs/sizes and enum-free MoonlightApplication/cancellation
records; ConnectionService calls are out of line. Compiler flags for UI pages,
streaming and the rest of the target are unchanged. The bounded loader/cancellation
path and 8/1 MiB pool sizes remain. A source check guards the scoped flag and ABI
assertions, but does not compile them. Maintainer rebuild and actual cover decode,
startup, Back/launch/stream-return checks remain **[open]**. Raw core memory is not
committed. Earlier source-only loader fixes did not resolve this ABI mismatch.

Paletted PNG correction (2026-10-30), **[code; P8 Vita gate open]**: the
maintainer's log now records successful Load/reduction/binding for apps `881448767`
and `1093255277` (600×800, stride 2400, GXM `0x0c000000`). Apps `1631604947`
and `717411297` also load successfully (528×704, stride 528, `0x95000000`) but
stop at phase 2 with no thumbnail. This is the native GXM `P8_ABGR` format,
not a decoder error or insufficient pool capacity: reported free bytes are over
5,000,000 versus 1,687,552 required. The reducer previously admitted only
32-bit RGBA/BGRA and therefore deliberately discarded those valid P8 surfaces.

The service now also admits `P8_ABGR` / `P8_ARGB`, obtains their 256-entry
native palette through public `sceGxmTextureGetPalette`, and rejects a missing
palette before locking/reducing. The existing bounded rectangle reducer reads
one index byte per source pixel, resolves its four color/alpha bytes before
averaging, and produces the same RGBA/BGRA thumbnail. Source stride/page bounds
use one byte for P8 and four for direct-color input. No full-size expanded image,
palette cache, decoder replacement or new pool reservation is introduced. The
source owns the palette until reduction/unlock completes and is still released
before thumbnail allocation. Unsupported formats retain the fallback; a missing
palette has a console-only diagnostic. User-facing strings/layout are unchanged.

Existing non-build checks now cover palette color/alpha averaging, index 255,
padded/truncated rows, enlargement, both P8 channel orders and missing-palette
rejection together with cancellation/failure/release ordering. The pixel case
failed against the previous reducer and passes after this correction; all 305
source checks pass. These checks interpret C/C++ source with mocks and do not
execute PAF/GXM. Maintainer gate: rebuild the application and verify the same
four covers, colors/transparency, Back/launch and stream return on Vita.

Only generated rows request images. The zero generation margin is passed as a
value-initialized `paf::math::v2()`: the installed SDK exposes private x/y fields
and no two-float constructor, so `{0.0f, 0.0f}` is not a valid argument. The
maintainer's second build compiled ApplicationService and stopped at that Apps
argument; the source correction retains the same zero-margin policy. Rebuild
remains **[open]**. PNG headers are bounded to 1024×1024 before
native decoding, resized to fit the 90×90 slot without cropping/stretching, and
published through an acquire/release completion flag. Unsupported/malformed,
missing, oversized or failed images leave the app launchable with its icon;
failures are console-only and are not retried every frame. The page caches at
most six thumbnails (nominal RGBA pixels under 190 KiB, excluding native
alignment/decoder overhead), evicting only ungenerated rows. Cache identity is
scoped to this Apps page/current host. Compressed PNG files now have an independent
per-PC disk cache; native surfaces/thumbnail pixels are not persisted.

Disk artwork cache (2026-10-30), **[code; Vita storage gate open]**:

- The host-control worker first checks `<key_dir>/<storage name>/app_<ID>.png`,
  normally `ux0:data/moonlight/<storage name>/app_<ID>.png`. It uses the configured
  root and an exact saved/paired host UUID lookup; display-name/address fallbacks
  cannot select another PC's cache. Storage names retain the existing traversal /
  reserved-name validation. No host directory/record or credential is created by
  artwork access. Rename of a PC's display name preserves its storage folder.
- Hits require age below 24 hours, a working/non-rolled-back wall clock, size
  33…512 KiB, the existing PNG dimensions bound (maximum 1024×1024), complete
  chunks ending at IEND, and matching chunk CRCs using the already linked zlib.
  Invalid, missing, stale, oversized, truncated or unreadable entries fall back
  to the existing pinned HTTPS `/appasset` request. Full image decoding still
  belongs to PAF; chunk validation is not a replacement PNG decoder.
- Authenticated session / current application-ID admission precedes disk access.
  A miss writes the original bounded PNG only after network success and before
  native decode, while cancellation/disconnect are checked before save and again
  before delivery. Cached bytes still pass through the same P8/RGBA/BGRA decoder,
  reduction and six-entry native thumbnail cache. Disk hits do not bypass pairing
  or expand the surface pool. No blocking I/O moves to the PAF main thread.
- Save uses `app_<ID>.png.tmp`, checks write/flush/close, then removes the old
  cache and renames the complete temporary file. This deliberately permits a
  replacement gap on Vita rather than relying on overwrite-rename semantics:
  interruption can leave a miss, never a published partial write. Failures are
  console-only and do not turn a successful artwork fetch into an error. This
  is not fsync/power-loss durability. Debug logs distinguish disk hit/save/failure.
- The existing host removal deletes all files directly in that host folder,
  including PNGs and leftover temporary files. No subdirectory cleanup path is
  needed. There is one file per fetched app ID; removed-app files remain until
  PC deletion (no disk LRU/pruning). Manually removing a cache PNG forces a fetch
  on a later disk miss, after any current RAM entry is released.
- All 310 non-build checks pass. Five new source-interpreted cases exercise
  actual path/PNG/read/write/API logic with mocked files, clock and CRC calls;
  they do not execute Vita stdio/stat/rename or PAF. Maintainer gate: rebuild the
  application, open/close/restart Apps and observe disk hits, compare two PCs
  with identical app IDs, corrupt/expire a PNG, exercise storage failure and
  verify PC deletion removes its cache. No new UI strings or locale keys.

Back and launch disable page input, mark the existing page transition guard,
cancel artwork and poll completion before starting navigation/control. LiveArea
admission also rejects an active artwork job; busy frame taps follow the existing
consume-without-replay policy. Widgets and cached/job surfaces release image
references before stream setup. Forced page destruction cancels without joining;
the job owns no UI pointer. Application shutdown drains the image queue before
backend/network teardown. Native image decoding itself is not preempted mid-call;
completion/cancellation discards its result. Native cleanup latency remains **[open]**.

Non-build checks interpret the actual reduction helper (channel order, padding,
averaging, enlargement, invalid dimensions/storage) and the job's loader/failure/
cancellation/release-before-thumbnail sequence using serial native mocks. They also
interpret PNG/aspect/transfer bounds, paired-session/app-ID
admission, late cancellation, job-result ownership and launch/Back ordering, and
validate resource references/localization. They do not execute PAF, native decode,
TLS, threads or the Vita ABI. Maintainer gate: rebuild RCO/application, compare
row/highlight/title placement and long names, scroll beyond the six-entry cache, try
portrait/square/missing covers, Back/launch during downloading, stream stop/return,
repeated page entry, and shutdown with a pending request. Appearance, focus,
real memory/latency and server compatibility remain **[open]**.

## 6. Recipes

### Interface localization — 2026-10-28

Startup failure handling (2026-10-29) **[code]**: bootstrap retains `Start()`'s
result. With an available UI plugin it uses ConnectionService's existing native
OK error dialog (`msg_error_startup`, EN/RU), then requests PAF shutdown after the
owned dialog has terminated or failed to open. A missing plugin skips the dialog
and requests shutdown directly. The module reports failure after runtime cleanup.
No inline fallback or extra page is created. Native startup/failure-dialog behavior
and translated appearance remain **[open]**; serial source checks are not Vita proof.

Repository migration, 2026-10-29 [code]: the native Licenses and credits
source-download link uses `https://github.com/NowaLone/vita-moonlight/releases`
in both EN/RU `msg_license_sources` strings. The shorter address preserves
the existing paragraph structure. Historical release/evidence links retain
the previous repository address.

English and Russian dictionaries in `cxml/locale/` are complete peers **[code]**.
The application plugin explicitly selects RU when the constructed PAF framework
reports `Locale_RU`, otherwise EN. Common resources and Sony's own system controls
keep their system locale. No custom language preference or settings-version change
is introduced. Language changes are applied on application startup.

Static CXML labels and AppSettings' `onGetStringCb` use the plugin's dictionary.
`ui_string()` supplies plugin-owned UTF-16 for PAF and both IME titles; those
resources outlive the dialogs. `ui_text()` uses native `Utf16ToUtf8` for copied
SceMsgDialog messages, dynamic labels and statistics. It clears output and logs
conversion failures. Transient UTF-8 results are consumed in the same expression
or held in an owning `paf::string`; no temporary `c_str()` pointer is retained.
Dialog ownership, busy/confirmation behavior and typed pairing results are unchanged.
Main's Delete confirmation uses a count-neutral phrase in both languages.

Connection/pairing messages and the statistics formatter remove incomplete final
UTF-8 characters after bounded writes. Dictionary checks preserve printf argument
types/order and ensure fixed dialog text fits the existing 512-byte buffers.
Names and server diagnostics are external content and are not translated. Copyright
holders, license names and upstream notices retain their original wording; the
credits introduction and source-download instructions are translated. The PNG
manual is unchanged.

LiveArea's generated welcome text uses the selected dictionary. The packaged
frame3 also has a native `<liveitem><lang>ru</lang>` variant with the same text,
using the language-selection pattern present in the local Sony Live from
PlayStation template. English remains the default. Content revision is 12;
frame3 revision is 7, other frame revisions remain 6. Reinstalling/updating the full
VPK is needed to validate packaged resources; no direct shell writes are used.

To add a translation, supply the same IDs and format placeholders in a new locale
XML, register it in the CXML stringtable, and add that language to `interface_locale()`.
Use dictionary IDs for new user-facing text. Vita input-language selection/URL address input
policy is independent of interface language. Existing geometry, native fonts,
selection bar and popup sizes are retained. Russian PIN paragraphs keep explicit
line breaks inside the existing 790 px width **[code; layout open]**.

Seven focused non-build checks cover dictionary/reference completeness, format and
buffer contracts, actual locale-selection and conversion branches, every UTF-8
truncation boundary (ASCII, Cyrillic, CJK and surrogate-pair output), typed pairing
messages/server details, and generated/packaged Russian LiveArea consistency.
Existing flow checks mock dictionary lookups with English text; LiveArea's mock
models UTF-8 bytes for either dictionary. These checks do not establish native
compilation/ABI, glyph rendering, resource selection or text fitting. Maintainer
build/Vita validation remains **[open]**: Russian and English starts; another system
language falling back to English; Main/selection/popup, PIN and Settings hints;
native busy/error/remote-Quit dialogs; IME titles; statistics; fresh and updated
LiveArea welcome. No agent build or hardware run.

**Russian missing-text regression (2026-10-28):** the maintainer's 960×544
screenshots `2026-10-28-144658.jpg`, `144702.jpg` and `144708.jpg` show Russian
Delete, an empty Settings button/title/busy message, and AppSettings displaying
`msg_*` IDs **[shot]**. This establishes partial Russian resource selection and
Cyrillic rendering, not successful localization. Read-only inspection of the
existing `build/vita_moonlight_ui.rco` finds both complete 155-entry dictionaries,
but incorrect length metadata in 133 RU strings and one EN string (`código`).
For example, `Настройки` occupies 18 UTF-16 bytes but is marked as 36. The local
Sony Live from PlayStation RCO records actual UTF-16 byte lengths **[code]**.

The pinned CXML compiler's `attr_type_wstring` uses `strlen(UTF-8) << 1`.
`scripts/patches/psp2cxml-utf16-length.patch` instead counts the written UTF-16
units, preserving offsets, string bytes and compression. CI applies this patch
before building the tool; the existing local compiler source is patched too.
The maintainer must rebuild **psp2cxml-tool first**, then the RCO/application,
selecting that rebuilt tool with `PSP2CXML_TOOL`. No dictionary/layout or runtime
lookup workaround is needed for the malformed length field. Two non-build
checks apply the patch to a pinned source fixture and interpret its counting
loop for ASCII, Cyrillic, accented Latin, CJK and surrogate pairs. Corrected
native appearance remains **[open]**; no agent build or Vita run.

**Add a page.** Add `<page id="page_x">` to the XML (first child: a `plane texture="_bg_texture"` of size
`960, 544`). Add a class deriving `page::Base` with `Base("page_x", "btn_close_x", open, close)`
and add the `.cpp` to `add_executable` in `CMakeLists.txt` (sources are listed explicitly). Own the event
callback and hand it back in the destructor. Open it with `new X(); if (!x->IsValid()) delete x;`. Add strings to
both `cxml/locale/en.xml` and `cxml/locale/ru.xml` in the same commit.

**Add a list row type.** Add a template with a 960 x 80 `list_item`, an `image_button` using
`style_image_button_host` or a dedicated row style (keep `focus_hint focus_shape="3"`), and optional `text` / `check_box` children with
ids that are unique to that template. Choose the template in the factory by state and fill it with
`set_child_text()`.

**Add a button to a bar.** Use `_common_default_style_button`, `adjust="2, 0, 0"` and `size="0, 46, 0"`, `pos y = 9`; put
two or more right-hand buttons in a horizontal `box` so they follow each other when a label changes. Use
`_common_sound_button_back` for back/cancel and `_common_sound_button_enter` otherwise.

**Disable a button.** `set_button_enabled(button, false)`. Do not use `SetActivate()` alone or `SetColor()`.

**Add a setting.** The settings UI is the system AppSettings plugin driven by `cxml/moonlight_settings.xml`:
add a `list` or `toggle_switch` entry (`id`, `title`, optional `hint`, `key`, `default_value`), its strings in
both `en.xml` and `ru.xml`, a `MoonlightSettingKey` value in `include/moonlight/types.h`, the key name in `key_name()` and the field in
`moonlight_settings_get_all()` (`src/moonlight/settings.cpp`), and a field in `MoonlightSettings` if the stream needs it.
Do not introduce a settings file or a custom settings screen.

AppSettings loads before the host store/Main during backend startup **[code, 2026-10-24]**.
Debug log defaults off and uses the switch callback's new value immediately; closing Settings
reapplies stored runtime values before logging/notifying closure. Both switch directions and
restart preference retention are accepted **[hw, user-reported, 2026-10-27]**.

**Page messages.** Keep only static empty-list labels and Pairing instructions/PIN.
Use ConnectionService's native busy/error dialogs for foreground progress/errors;
return Main to its empty-state policy through `Main::ShowIdleStatus()`.

**RFI setting correction (2026-10-27) [code; build/Vita pending].**
`moonlight_video_set_stream_options()` prepares decoder capabilities before the stream
worker enters common-c. Updating the original callback struct inside decoder setup was too
late for common-c's copy and could apply the previous connection's value. The setting and
its default remain unchanged; first connection and subsequent On/Off snapshots are source-tested.

**Settings wording correction (2026-10-27) [code; build/Vita pending].**
The existing sections and all 29 controls, keys, defaults and stored choice values remain.
Bitrate displays Mbps (stored kbps); two-finger scroll speed displays its actual multiplier
`1 + value / 100` and applies only in Mouse Absolute mode. Back-touch margins use pixels in
the virtual 960×544 area. Labels distinguish host graphics/audio, motion sensors, screen
cropping, VBlank and presentation limiting. Remote detection still maps On to AUTO and Off
to LOCAL; this is a wording correction, not a connection-policy change. Hints explain PS
single/double/hold actions, special touch zones requiring mode Off, and custom face mappings
overriding X/O swap. Keyboard language selects the native IME. AppSettings version stays 1.

**Sprint settings removed (2026-10-27) [code; build/Vita pending].**
At the maintainer's request, double-tap sprint and its interval are removed from native
Settings, localized text, settings reads/types and the input runtime. Stick double taps no
longer synthesize L3; existing rear/front touch L3 controls remain. Old sprint keys are never
read. The other 27 controls keep their groups, keys, defaults and choices; settings version
stays 1 so the remaining preferences are not reset.

**Special-key stream exit (2026-10-27) [code; build/Vita pending].**
With `Enable touchscreen special keys` enabled and `Touchscreen mode` Off, the top-right
zone (`x > 820`, `y < 100` in virtual 960×544 coordinates) now requests the existing
asynchronous `moonlight_stream_stop()` and returns from the input poll immediately.
It replaces the former right mouse click and works with PS capture On or Off. The
existing touch latch prevents repeating while held. Top-left keyboard and bottom L3/R3
zones retain their actions. This ends the local stream, not the application on the PC.
The native Settings hint describes the new action; keys/defaults/version are unchanged.

**Keyboard category (2026-10-27) [code; build/Vita pending].**
`On-screen keyboard language` now follows Touchscreen mode in Input. The former Keyboard
root category is removed. Its `keyboard_layout` key, default and five language values are
unchanged, as are the other controls and AppSettings version 1.

**System input languages (2026-10-29) [code; basic Vita acceptance below].**
Stream's native IME now uses `supportedLanguages = 0` and `languagesForced = SCE_FALSE`,
delegating input languages and switching to the Vita's system configuration. This
supersedes the five-choice Moonlight setting above. The native language switcher
requires multiple keyboards enabled in Vita Settings → Language → Input Languages.
The [Sony keyboard guide](https://manuals.playstation.net/document/en/psvita/basic/osk.html)
describes this system behavior. Main's manual-address IME retains its forced English
URL mode, ASCII address validation and module/dialog ownership.

The keyboard-language control, six EN/RU resource entries, setting enum/field/read,
runtime storage/getter and parameter plumbing are removed. The old stored key is
ignored; AppSettings version remains 1. All other 26 controls retain their keys,
defaults and choices, so unrelated preferences are preserved. Enter/Cancel, the
120-unit stream text limit and the existing UTF-16 → UTF-8 text transport remain.
One new non-build check interprets the actual dialog setup/admission block with
module/open failures and duplicate-open gates, asserting system-language parameters.
The existing sender check covers additional Japanese, Korean, Chinese and Turkish
text. These mocks do not establish native IME switching or host reception.
After `f273c72`, the maintainer replies “всё ок” **[hw, user-reported, 2026-10-29]**,
accepting the basic system-language keyboard change. No package hash, profile,
log or individual Enter/Cancel, language/host-application and failure-case results
were supplied. Do not reopen the accepted basic check without a regression;
the broader matrix remains unverified. No agent build or hardware run.

**Licenses and credits (2026-10-27).** The native Settings root now includes
`licenses_settings`, titled `Licenses and credits`, using the existing
`setting_list style="edit"` / `label style="heading"` information pattern
**[code]**. Read-only labels identify the Moonlight/transport/parser/crypto/codec
and SDK contributors, component license names, the original mDNS permission and
OpenSSL acknowledgments. The final label gives the project's Releases address
for source archives containing full license texts; this screen is an attribution
overview, not an offline full-license reader or a new project-wide license grant.
All strings use `cxml/locale/en.xml` and the existing AppSettings GetString
callback. No persistent keys/defaults or settings version change is needed.
The focused resource check verifies read-only elements, localized references,
component coverage and acknowledgments. The maintainer accepts readability/scrolling
and navigation **[hw, user-reported, 2026-10-27]**; no agent build or Vita run.

## 7. Matching a reference screenshot

1. Use 960 x 544 screenshots of the reference screen and of this app's screen in the same state.
2. **Edges:** along a row or column that crosses the shape but not its text, take the absolute difference of
   neighbouring pixels and keep the peaks. Run the same detector on both images and compare visible edges.
3. **Positions:** convert to layout values with the known inset (section 2.2); change `pos` in 1 px steps.
4. **Colours:** sample a band that has no widgets, above and below the element, and solve
   `result = bg * (1 - a) + c * a`. Remember that style and `planeobj` colours multiply, and that JPEG blurs 1 px lines.
5. **Text size:** compare flat capital cap heights against fonts known in this app; confirm by overlaying.
6. Record the numbers and their source here and in the commit message, tagged **[shot]** until a hardware check.

## 8. Pitfalls

- `DeleteCell(0, 0, existing - 1)` leaves a stale row.
- A `style_plane` colour set in both the style and the `planeobj` is squared.
- `_common_texture_ruled_line` has a 4 px source height with transparent outer rows; do not
  compress it to the former 2 px project-line height without checking the rendered result.
- `SetActivate()` does not dim a button; `Widget::SetColor()` on a disabled button was rejected in favour of the native
  disabled state.
- Showing and hiding a checkbox on a shared row template misbehaves; use the select template.
- Main's empty-state label must stay hidden over nonempty rows (use `ShowIdleStatus()`).
- Do not restore host Copy / `SceClipboard`, and do not add long-press or per-item popup menus.
- Hardware-only checks are tracked in `ROADMAP.md`; do not tick them without a Vita run.
