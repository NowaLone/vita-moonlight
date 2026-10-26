# Dynamic LiveArea

Source implementation on `codex/livearea-dynamic-frames`, based on `master`
`721cca0` (2026-10-24). The maintainer supplied a screenshot with four app names
and `NA-IGRUNOV.LOCAL`, then confirmed that the elements change on Vita.
This accepts basic dynamic display on that device, without per-profile logs.
The 2026-10-25 screenshot showed app labels without backdrops and the PC label
without an icon; the row/card artwork and frame-launch support were revised later.

On 2026-10-26 the maintainer replied “всё ок” to the requested fresh-VPK check:
installation after the PNG fixes, replacement icon/startup appearance, PC/app
labels, activation of the cards and retention after app closure/reboot. This is
user-reported basic Vita acceptance following source revision `6e1a893`, not an
agent-run build/test. No tested package hash, runtime log, firmware or separate
normal/system results were supplied. Short/empty lists, fresh welcome defaults,
host switching, separate cold/resumed delivery and stale/busy/cancel/error cases
remain the broader device procedure below; do not repeat the accepted basic
check without new evidence of a regression.

For the toolbar's blue refresh action versus application binary updates from
GitHub/NeoVitaDB, see [application update research](APP_UPDATE_RESEARCH.md).

## Behavior

- The original `bg0.png` is packaged without painted text or a top-left caption.
  Native welcome text lives in frames; the package display name is Moonlight.
  Caption admission for the current profiles is documented in the evidence below.
- A successful connection captures the selected PC's display name (address if
  unnamed) for frame7 and clears the previous six application labels. Failed
  attempts leave the last successful snapshot alone.
- Successful Apps retrieval copies the first six entries in backend order into
  frames1–6. Shorter lists clear unused rows; an empty list shows the welcome
  text described below. Cache reads
  happen after the worker completes and before a page callback can start the
  next workflow. Publishing does not request another application list.
- Populated app slots use the Browser's 472×48 row artwork as `app_row.png`,
  losslessly converted to indexed PNG: black body at alpha 97/255, original
  rounded corners and perimeter. A generic Moonlight icon appears at 32×32
  before the 22 px regular system label. Text is left-aligned, centred vertically,
  with 50 px left/16 px right margins and ellipsis. Unused rows have no
  background, image or target.
- Frame7 uses the same Browser background style in a 280×158 `pc_card.png`,
  adapted with fixed 8 px corner/edge caps to preserve border thickness and
  rounding. Its black body has alpha 97/255, matching the app rows. Width matches
  the 280 px gate startup image; the transparent 80×80 `pc.png` and centred 22 px
  name remain in their existing positions. Native gate/focus borders are outside
  this content width.
- With no app names, frame2 shows “Moonlight” (28 px white) and frame3 shows
  “Open source game streaming client” (20 px light gray), centred in the left
  column. These are regular, shadow-free native XML strings using the system
  font, not text rasterized into `bg0.png`. There are no welcome launch targets.
  A connected PC card can coexist with this empty Apps state.
- Frame7 connects to its saved PC and opens Apps (or the native PIN workflow
  if pairing is required). An app frame connects to that PC, obtains fresh Apps
  and starts the selected **application ID**, even if its list position changed.
  Missing PCs/apps produce native errors. Empty slots and snapshots without a
  server UUID have no launch target.
- This is the last snapshot obtained while Moonlight runs. No background
  network refresh runs after the app closes. Shell retention across app closure
  and reboot is a device gate, not established by the source checks.
- The packaged template starts with the same welcome text, without sample app/PC
  names, backgrounds or targets. The old purple `frame1.png`–`frame7.png` assets
  remain removed. `app_row.png`, `app.png`, `pc_card.png` and `pc.png` are
  explicitly packaged for dynamic updates. Content revision is 11; frames1–7
  are revision 6.
  No startup publish occurs before a successful connection, so installation
  defaults or the previous shell snapshot remain until then.

Reinstallation correction (2026-10-24): the maintainer reported purple defaults
returning after reinstall. The previous background removal affected native
updates only; the shipped XML still referenced all six purple assets and the
sample `Desktop`/`NA-IGRUNOV` labels. The packaged defaults above now remove that
source of the regression. Fresh VPK installation is accepted in the 2026-10-26
basic check; that reply does not separately itemize empty/welcome defaults.

## Layout references (2026-10-25)

The supplied a5 RCO fixes app frames at 480×68 with a 68 px vertical step and
frame7 at 360×210. Its background origin is the centre of the 840×500 paper,
(480,294) on the 960×544 screen, rather than the in-app PAF origin. The new
472×48 app backdrop with x=6, y=2 occupies screen x=70…542; the first row is at
y=140…188, including the source PNG's transparent outer pixels. Its icon box is
x=80…112, y=148…180; the label begins at x=120, leaving 8 px after the icon.
These match the Browser screenshot's first-row artwork fit described below,
while retaining a5's 68 px vertical step for six app slots.
Frame7's new content is top-aligned within its existing frame, at x=580…860,
y=330…488. The gate startup image is 280×158; the a5 gate outer box is 292×170.
Exact focus-border extents and visual matching remain device checks.

The 28 px regular heading follows the shared shell caption style found in the
supplied RCO. The smaller 20/22 px strings and alignment/wrapping attributes use
native LiveArea text controls, as in the
[VitaSDK sample](https://raw.githubusercontent.com/vitasdk/samples/master/pretty_livearea/sce_sys/livearea/contents/template.xml).
These are reference-based choices, not a claim of conformance to an unavailable
Sony typography specification. The
[VitaSDK parsed layout declarations](https://raw.githubusercontent.com/vitasdk/vita-headers/master/include/psp2/lsdb.h)
include visual-element dimensions/offsets, background origins and text margins.

`tools/generate_livearea_backdrops.py --browser-archive /path/to/sce_sys.7z`
imports the original `LA_window.png` through 7z and Pillow. Its 62 distinct RGBA
colors fit in an 8-bit palette; the importer rejects unexpected dimensions/color
counts and verifies decoded pixel equality before writing `app_row.png`. Decoded
RGBA SHA256 is `cae8206c1aace173617d6bccab5a342d11b51e2ce2d83fb825697c59a7e061fb`.
CMake packages the existing 128×128 indexed `sce_sys/icon0.png` under the
additional destination `sce_sys/livearea/contents/app.png`; no duplicate source
PNG or generation step is needed. LiveArea scales it to 32×32 as a generic
app marker. The Browser WWW icon is not packaged.

The script derives the 280×158 PC card from the imported row with nine-slice
resizing in indexed mode. The four 8×8 corner patches keep their original pixels;
only the intervening edge strips and centre change length/area, using nearest
sampling with the original palette and alpha. Pixel checks confirmed unchanged
corners/edge thickness and the same black/97 body. Pillow is required for card
generation; 7z is needed only for importing the archive. Running without
`--browser-archive` leaves the imported row untouched. `pc.png` remains the
unchanged indexed PC icon from commit `374c436`. Card geometry, icon/name positions,
spotlight, gate, welcome text and UUID/app-ID launch flow are preserved. Appearance is source
implemented; no resource compilation or Vita call was run by the agent.

## Browser resource comparison (2026-10-25)

Read-only reference: maintainer-supplied `sce_sys.7z`, SHA256
`ed5095e803d5589cbb375cf6506ff8bca79e93f4c357c997d54487c9d5cd534b`.
The initial inspection used a temporary directory. At the maintainer's subsequent
request, the row artwork is now copied into Moonlight as an indexed PNG; the other
Browser assets and its ten-frame template are not imported.

- `sce_sys/livearea/contents/LA_window.png` is 472×48, grayscale with alpha
  (PNG color type 4). The body is RGBA (0,0,0,97), about 38% opacity. Visible
  pixels occupy [1,1,471,47), with rounded antialiased corners and a subtle
  perimeter: the straight top edge is (53,53,53,106), and bottom edge alpha
  reaches 118/255. This is an image with its own edge pixels, not a plain fill.
- Browser's teal comes from its 840×500 `bg0.png` showing through the black
  window. Compositing the black/97 body over that actual background predicts
  interior pixels in the supplied screenshot with mean absolute RGB-channel
  errors of 0.80, 0.81, 0.97 and 1.17 for the first four rows. Samples exclude
  icons/text and use screen x=140…518 with a 2 px step. These are offline image comparisons, not Vita tests.
  Edge matching places the first PNG near (70,140) in the screenshot; exact
  native layout coordinates are not established by this fit.
- `favicon.png` is a separate 32×32 grayscale/alpha WWW icon. The screenshot
  shows it before the label; Moonlight adapts this composition with its own
  32×32 Moonlight marker instead of WWW.
- Browser's packaged `template.xml` selects `style="browser"` and declares ten
  empty frame/liveitem slots. It supplies no per-row text, targets, icon or window
  references. The populated screenshot therefore reflects runtime content;
  runtime XML, font size and precise icon/text offsets cannot be recovered from
  this archive alone. Moonlight uses `style="a5"`, seven frames and explicit
  runtime background/text markup in `LiveAreaService`.

The comparison establishes the original row artwork. A black translucent row
will darken its underlying artwork and has little contrast on Moonlight's black
areas; changing only its alpha cannot reproduce Browser's teal surroundings.

## Native boundary and ownership

`MoonlightApp` owns `LiveAreaService` and drives it on the PAF main thread.
`ConnectionService` retains a value copy of the selected host; only
`CONNECTION_READY` with result 0 publishes it. `APPLICATIONS_READY` captures at
most six cached names. Names are bounded, escaped for XML and invalid UTF-8/XML
characters are replaced before submission.

After successful connection, `HostService::Resolve` obtains its saved UUID: an existing UUID must
match exactly; an attempt without one (e.g. manual input) can match the saved
address/port. Display names are never used for launch identity.

Published targets use `psla:moonlight1/<hex-encoded-host_id>/<application_id>`;
ID 0 selects only the PC. Each frame carries its own host identity, so a partial
seven-frame update cannot silently redirect an older app link to the newer PC.
The format is bounded and versioned, with strict hex/decimal parsing and integer
overflow rejection. It contains no credentials, filesystem paths or connectable
address supplied by the URI. No separate last-PC/shortcut storage file is added.

`MoonlightApp` polls AppMgr's application-event count every 100 ms while its
main-thread callback runs, including after resume. Only AppUtil event type 5 is
parsed; ordinary type 0 gate launches and other events are ignored. The pinned
AppUtil prototype has a raw output pointer, so the platform binding supplies the
SDK's 1019-byte parameter plus 32 reserved bytes, with an exact-size assertion.

A validated request resolves the UUID against the current saved-host store,
then uses Main's existing connection path. Only idle Main/Apps can accept it;
an idle Apps page returns through the existing page stack first. PIN, Delete,
IME, OptionMenu, Settings, foreground busy and streaming/paused states reject
the request with a log, without queueing it for later or interrupting the owner.
The pending app ID belongs to the connection/PIN/Apps pages and is consumed once
after fresh Apps. Back/cancellation, connection/pairing/list errors and page
destruction discard it. Starting still uses `Apps::SelectApp` → ConnectionService:
the native Yes/No confirmation is required before quitting a different host app.

The publisher loads `SCE_SYSMODULE_LIVEAREA` before its first native call and
keeps it resident until process exit, including any request still owned by
SceShell during shutdown. It links the existing `SceLiveArea_stub`. The pinned
VitaSDK includes that stub/export database but lacks `psp2/livearea.h`, so
`include/platform/livearea.h` declares only the two native exports used.

Each request sends a single `<frame>` XML string to
`sceLiveAreaUpdateFrameAsync("01.00", ..., "app0:sce_sys/livearea/contents", 0)`.
Populated slots reference only the packaged row/card/icon assets in that read-only
asset directory; empty/welcome slots reference none.
Argument 0 matches both
the older SDK's no-option value and current VitaSDK's normal layer; the
inconsistently documented value 1 is unused.

Only one request is in flight. `sceLiveAreaGetStatus()` is polled once per main
tick until success or error; submission success alone is not completion.
Latest snapshots coalesce while a request is pending. App frames are submitted
before frame7, with no new submissions during foreground busy/streaming/paused
states. A pending operation is still polled. This is **not atomic across seven
frames**: partial updates or mixed old/new content can be visible during a
batch or after an error. An error stops that batch without repeated retries;
a newer snapshot can publish again. Module-load failure disables publication
until restart. Shutdown discards unsent work without waiting on SceShell.

Diagnostics use `[LiveArea]` through `vita_debug_log()` (enable Debug log in
Settings). There are no file logs, writes to `app0`/`appmeta`, database access,
promoter calls, module unloads during PAF, timed waits or main-thread sleeps.

## Maintainer validation

Build the complete branch VPK with the ordinary build procedure. The agent runs
no build, packaging, deployment or Vita calls.

1. Inspect LiveArea after installing the complete VPK, before opening Moonlight:
   check the original spotlight background without a top-left caption;
   expect the two welcome strings, without row/card backdrops or sample labels.
   Then enable Debug log,
   connect to PC A, obtain Apps, and wait for frame1–7
   `complete result=0x00000000` before closing. Inspect the LiveArea names:
   populated app rows must have the original translucent Browser backdrops,
   32×32 Moonlight markers and left-aligned labels with an 8 px icon/text gap;
   frame7 must show the transparent PC icon and name in a gate-width card
   with the same translucent fill, rounded corners and thin perimeter. Check
   that its larger height does not stretch the corner/edge thickness, the name
   does not overlap the icon and the card stays within the paper.
2. Connect to PC B with a different name/list, including more than six apps.
   Check backend order and that only its first six names remain.
3. Exercise fewer than six apps, an empty list, failed connection and failed
   Apps retrieval. Connection failure must retain the prior successful snapshot;
   a newly connected PC must not retain the previous PC's labels after a
   successful clearing batch. Empty Apps must show both welcome strings and
   retain the connected PC card; a shorter nonempty list must leave unused rows
   without stale backgrounds, icons or targets. Note partial native failures separately.
4. Check long names, Cyrillic, `&`, `<`, quotes and ordinary frame activation.
   Check Main/PIN/Settings/stream launch-stop-reconnect for regressions.
5. Check the completed snapshot after full app closure, opening/closing the
   LiveArea, reopening Moonlight without connecting and rebooting. Repeat for
   both normal and system profiles. No `app.db` inspection/replacement or
   database rebuild is part of this procedure.
6. After installing this revision, connect and retrieve Apps once to republish
   the new targets; earlier `psla:eboot` links only open Moonlight. Wait for a
   completed publication, then fully close Moonlight. Tap frame7 and check
   connection/Apps. Repeat from an app frame and check connection → fresh Apps
   → selected stream, including the PIN path where applicable.
7. Repeat taps from suspended idle Main and idle Apps. Check that pending
   operations, PIN, settings/IME/selection and an active stream are preserved;
   rejected taps must not launch later when the current workflow finishes.
8. Delete the saved PC locally and activate its older published frame: expect
   the saved-PC error. Remove/reorder an app on the host: fresh IDs determine
   selection, and an absent app must show an error without launching a neighbour.
   Check PIN cancellation and Apps/connection failures for no delayed autolaunch,
   plus the existing remote-Quit Yes/No flow with another host app running.

## Evidence

- **2026-10-26, maintainer reply “всё ок”:** acceptance of the three requested
  basic checks (fresh VPK/icon/startup; labels/card launch; closure/reboot
  retention). Source HEAD at confirmation was `6e1a893`; the tested artifact and
  profile were not independently identified. Remaining validation above is not
  claimed complete by this reply.
- [Settings RCO recheck](SETTINGS_UI_RESEARCH.md#livearea-caption-recheck-2026-10-24)
  distinguishes the in-app header from the missing LiveArea caption. A prior
  external template's `<title>` example did not establish that our shell would
  display a caption for this app.
- [Shared shell title template](SETTINGS_UI_RESEARCH.md#shared-livearea-title-template-2026-10-25)
  is now found in the supplied `livearea_plugin.rco`: a separate 28 px regular
  top-left text widget, with no static label and a white default style.
- [Supplied shell instruction trace](SETTINGS_UI_RESEARCH.md#shell-caption-admission-traced-2026-10-25)
  matches the RCO hashes and runtime name/color setters. Caption creation admits
  presentation kind 0, whereas both current categories (`gd` / `gdc`) select
  kind 1 and skip it. Changing the system-build flag, layout or text color does
  not bypass the check. The maintainer subsequently requested no texture caption.
  Launch categories remain unchanged; firmware identity and that installation's
  exact metadata were not verified. No shell/database modification was performed.
- [VitaSDK LiveArea API](https://docs.vitasdk.org/group__SceLiveAreaUtilUser.html)
- [VitaSDK export database](https://github.com/vitasdk/vita-headers/blob/master/db/360/SceLiveAreaUtil.yml)
- Local SDK `target/include/livearea.h` and samples
  `system/api_livearea/basic` and
  `system/tutorial_shooting_game_trc_compliant/gamelog_manager.cpp` show direct
  frame updates, including dynamic score text. They were read, not built/run
  or copied into this repository.
- Non-build checks interpret the actual XML builder, snapshot, publisher and
  main-thread capture/gating, target parser, saved-host resolution, one-shot
  application selection and native-event poll with serial API mocks. Page
  constructor/PIN argument handoffs are source-inspected. They do not validate native
  compilation, ABI behavior, shell persistence, timing or real concurrency.
