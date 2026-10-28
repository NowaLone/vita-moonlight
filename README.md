# Vita Moonlight PAF

Native PS Vita Moonlight frontend built with Sony's PAF framework.

The project provides a system-style PAF UI on top of the real Moonlight/GameStream stack used by Vita Moonlight. It is no longer just a UI shell: host discovery, persistence, pairing, application listing, streaming, video/audio output, and Vita input paths are implemented.

For VPK/profile selection, Sunshine pairing, controls, updates and troubleshooting,
see [Install and use](docs/INSTALL.md). Maintainers use the
[release procedure](docs/RELEASE.md) for versioning, artifacts and validation.

## Architecture

The project is intentionally split into a frontend/service/backend stack:

```
PAF Page
  ↓
MoonlightApp
  ↓
Services
  ↓
MoonlightBackend
  ↓
LegacyMoonlightAdapter
  ↓
legacy GameStream / Moonlight streaming code
```

The PAF layer is responsible for UI and navigation. Streaming protocol, GameStream, networking, decoding, audio and device input remain below the frontend boundary.

## Features

The current application supports:

- Native PAF main screen and page navigation.
- Inline manual PC address input with the native Vita IME (`host` or `host:port`).
- Native system connection loading and error dialogs.
- System-style title bars and list views based on the patterns used by Vita system applications and `GrapheneCt/NetStream`.
- LAN/mDNS PC discovery.
- Saved PC list with native-style Delete multi-selection and native checkboxes.
- Native delete confirmation and persistent host removal.
- Moonlight PIN pairing.
- Retrieving the application list from a paired PC.
- Confirmed remote Quit when another application blocks launch, followed by the selected app
  (maintainer reports successful Vita testing, 2026-10-23; fault/race cases remain open).
- H.264 video streaming and Vita AVC presentation.
- Opus audio playback.
- Optional stream statistics overlay: video rates, missing/local-drop estimates, RTT,
  decode/PAF queue timing and payload bitrate. The compact six-line overlay is accepted by
  the maintainer on Vita (2026-10-27); independent metric benchmarks remain separate.
- Vita controller input.
- Front touchscreen input.
- Motion/gyro input path. Raw sensor units/axes, report-rate races and system-UI gating are source-corrected
  (2026-10-27). The maintainer tentatively reports the changes working on Vita;
  precise sensitivity, fault recovery and endurance are not individually verified.
- Optional host-controller RGB overlay: Off, Like DualShock 4 or Like DualSense; source
  implemented in bff5712, with build/Vita appearance and host feedback validation pending.
- PS Button/application lifecycle handling.
- Session-owned stream stop/disconnect cleanup and reconnect, with scoped Vita evidence.

## Repository Layout

```
src/
  main.cpp
  app/                 PAF runtime and MoonlightApp
  pages/               PAF pages and navigation
  services/            host/discovery/pairing/connection/apps/settings
  backend/              backend abstraction and legacy adapter
  backend/legacy/       Vita Moonlight/GameStream compatibility code
  moonlight/            Moonlight API, stream session, Vita renderers/input
include/               project headers
cxml/                  PAF UI and AppSettings resources
third_party/
  moonlight-common-c/  Moonlight streaming implementation
  enet/                ENet transport
  inih/                INI parser
  h264bitstream/       H.264 parsing support
```

## UI

The UI is implemented with PAF CXML resources.

English and Russian interface dictionaries are source-implemented. The application
selects Russian when PAF reports the Russian system locale, and English otherwise.
Pages, native Settings content, dialogs, IME titles, stream statistics and LiveArea
welcome text use these resources. Keyboard layout remains a separate setting;
PC/app names and server messages retain their original text. Third-party notices
retain their original wording, and the existing PNG manual is unchanged.
Build, language selection and translated layout on Vita remain unverified.

The current list/title resources intentionally follow the real patterns used by `GrapheneCt/NetStream`, including:

- `template_top_title_bar`
- `template_flow_bar` (pairing bottom bar, sharing Main's translucent selection-bar styles)
- `template_list_view_generic`
- `template_list_view_main` (main-page host list, shorter so it clears the bottom bar)
- `template_list_item_generic`
- `template_host_list_item` (saved-PC row with a title and a description)
- `template_host_list_item_select` (saved-PC row with a checkbox, used only in selection mode)
- `style_list_view_generic`
- `style_image_button_list_button`

The full UI reference (screen zones, layout language, pages, templates, styles, helpers, measured values from PS4 Link and Photos, recipes and pitfalls) is [`docs/UI.md`](docs/UI.md).

Foreground Connect, Apps loading and stream setup use PAF CommonGuiDialog's compact
`s_dialogTextSmallBusy`. Errors and Delete OK/Cancel use SceMessageDialog. Pages show static
empty-list labels and pairing instructions; no inline progress or success/status fallback.

Main contains one list: saved PCs first, temporary LAN discoveries below. Discovery runs
quietly in one backend worker, repeating the mDNS query five seconds after the previous send
completes. There is no Search PC page/button or search modal. Only saved rows have the existing
TCP availability indicator; temporary rows keep the same columns without a dot. The top-left
PC-plus button opens manual entry in the native Vita IME; the corner menu opens Delete/Settings.
Discovery pauses during those flows, foreground operations, other pages and app suspension;
UI never waits for its worker.
Temporary results age out after 15 seconds of active healthy discovery without another observation;
pause and detected network failures freeze aging. Clicking a temporary PC connects without saving;
only successful PIN/HTTPS pairing saves a new PC. See [UI behavior and validation limits](docs/UI.md#main-background-discovery--2026-10-23).
The maintainer confirms PC discovery already works on Vita (2026-10-27). Basic discovery
is accepted; detailed timing, focus and pause/fault cases were not individually reported.

Saved hosts use the Vita system-app selection/action pattern. The standard bottom-right corner button opens a project-owned PAF `speech_balloon` action menu (not a discovered Sony system action-menu API) with **Delete** at the top and **Settings** at the bottom. Choosing Delete turns the saved-PC list into multi-selection mode with PAF checkboxes (tapping or activating a row toggles it) and a bottom action bar with Cancel, Select All/Deselect All, and Delete. Delete asks for confirmation through the native `SceMessageDialog`; no host-copy/clipboard action is provided. The earlier saved-only selection UI was verified on Vita, including popup placement, Delete/Settings focus, row/checkbox positioning, action-bar layout, Select All/Deselect All focus, disabled Delete behavior, confirmation, and post-delete list refresh/focus. Delete is disabled when there are no saved PCs or nothing is selected; its disabled appearance uses PAF `ButtonBase` state and keeps the button background black while rendering the label gray.

PAF uses a **center-origin 960×544 coordinate system**:

- `(0, 0)` is screen center;
- positive Y points upward;
- positions are relative to the parent center rather than CSS-style top-left coordinates.

## Settings

Application settings use Sony's **SceAppSettings** service.

The declarative settings UI is:

```
cxml/moonlight_settings.xml
```

The adapter is:

```
src/moonlight/settings.cpp
```

Settings such as resolution, FPS, bitrate, touch mode, controller type, gyro and other streaming/input options are stored through AppSettings.

AppSettings loads during backend startup, before saved hosts and Main are populated.
The saved **Debug log** preference therefore applies without opening Settings first.
Its switch applies the callback's new value immediately; closing Settings reapplies
the stored runtime values before the closing memory diagnostic. Default logging is off.
The maintainer accepts toggling and preference retention after restarting (2026-10-27).

The project does **not** use the old `moonlight.conf` settings model.

**Settings → Licenses and credits** provides read-only component attribution,
license names and OpenSSL acknowledgments, plus the Releases address for source
archives containing the full license texts. The native AppSettings section is
accepted by the maintainer on Vita, including readability/scrolling and navigation (2026-10-27).

## Host Persistence

Saved PCs are intentionally separate from AppSettings. Host state is owned by the host store, while the client identity is shared by the entire Vita installation.

The storage model is:

```
ux0:data/moonlight/
    client/
        uniqueid.dat
        client.pem
        key.pem
        client.p12
    <storage name>/
        device.ini
        server.pem
```

The `client/` directory contains the single global GameStream client identity. Every PC uses the same client `uniqueid.dat` and RSA certificate/key.

Each host record stores metadata:

```
host_id
paired
internal
external
mac
port
prefer_external
```

`host_id` is the GameStream/Sunshine server UUID obtained from `/serverinfo`. It is the persistent PC identity; the display name and IP address are discovery/connection data, not client-identity storage keys.

Discovery results are temporary. Selecting a discovered PC or entering an address manually (including a custom port) keeps it unsaved through connection and PIN entry. Only successful PIN/HTTPS pairing saves the PC with its server UUID, paired state, MAC and server certificate. Cancellation or failure leaves no new saved PC. Authenticated reconnections can update an existing paired record.

The host store resolves the selected record to `<storage name>/server.pem`; this is the public
Sunshine/GameStream **server** certificate, never the global Vita client certificate or key.
Only successful PIN proof and a matching final HTTPS pairing challenge establish a pin.
Subsequent HTTPS requests verify the complete paired leaf certificate. Old records without
`server.pem` require pairing again. An unreadable/malformed pin or changed server certificate
fails closed: remove that saved PC locally and add/pair it again to establish new trust.
Local deletion removes its server pin as part of the host directory; it does not revoke the
Vita identity on Sunshine. A pin persistence error is logged separately from pairing success;
trust then lasts only for the current connection and pairing is needed after restart.
The implementation requires the OpenSSL libcurl backend. On 2026-10-20 the maintainer confirmed
normal PIN pairing, Apps, application restart, reconnect without another PIN and stream launch/stop.
On the same date a mismatched valid saved server certificate was rejected with security result -10;
restoring the original allowed connection and retrieval of four apps. Other certificate/error cases
and the full TLS/runtime matrix remain pending; see the API audit.

The project does not provide compatibility or migration for the original Vita Moonlight per-host credential layout. Existing per-host `uniqueid.dat`, `client.pem`, `key.pem`, and `client.p12` files are not used by the new global client-identity implementation.

Deleting a saved PC currently removes its local metadata; Sunshine retains the Vita's paired-client
record. Remote self-unpair is requested in [ROADMAP.md](ROADMAP.md), but stock Sunshine exposes
revocation through its administrative API, not its paired streaming-client API. Administrative login
on Vita is outside the agreed scope. Until a client self-revocation protocol is available, remote
revocation is performed in Sunshine's own client-management UI.

## Build

The inspected SDK/component revisions, dependency versions, file fingerprints and setup
procedure are recorded in [docs/BUILD_ENVIRONMENT.md](docs/BUILD_ENVIRONMENT.md).
The base SDK archive is recovered and verified. On 2026-10-24 the maintainer's
[clean CI run](https://github.com/NowaLone/vita-moonlight-paf/actions/runs/40052743854) rebuilt the
pinned dependencies and both application profiles successfully at `4076f15` (208 source checks).
The maintainer subsequently confirms the requested basic startup/Settings/stream/reconnect
Vita smoke (“всё ок”, 2026-10-24); this establishes basic user-reported acceptance of the CI baseline.

Pushing a version tag such as `v1.01` starts
[Clean Vita build](.github/workflows/build.yml), builds the system profile and
automatically publishes its complete GitHub Release. The tag selects Vita version
`01.01`; both lightweight and annotated tags are supported. There is no manual,
branch-push or PR trigger. Each run rebuilds the pinned dependencies without caches.
Version/tag rules and release checks are in
[the release procedure](docs/RELEASE.md).
Download the packages/debug ELF and build-evidence artifacts from the completed run;
evidence is also saved on failure. See [CI setup and limits](docs/BUILD_ENVIRONMENT.md#github-actions).
The successful run was started by the maintainer; the agent did not run a build or dispatch CI.

Requirements:

- [VITASDK](https://github.com/vitasdk/vitasdk)
- [vitasdk-paf-component](https://github.com/Princess-of-Sleeping/vitasdk-paf-component)
- [psp2cxml-tool](https://github.com/Princess-of-Sleeping/psp2cxml-tool)
- `psp2shell_cli` only if using separate local deployment tooling

Typical setup:

```bash
export VITASDK=/usr/local/vitasdk
```

Build the default system profile:

```bash
bash build.sh
```

This compiles CXML and the system profile in `build/`, producing
`build/vita_moonlight_paf-system.vpk` and matching debug ELF/SELF files.
Generic `build/vita_moonlight_paf.{vpk,self,elf}` paths are also retained.
System is the distributed profile; CI and Releases do not publish normal packages.

The ordinary profile is an optional local build, selected explicitly (maintainer command):

```bash
bash build.sh -DMOONLIGHT_SYSTEM_APP=OFF
```

It uses the same `build/` directory and produces the `-normal` copies instead.
Both profiles use title ID `VLMP00001`: installing one replaces the other.
Without a profile argument, the script selects system even if an old cache selected
normal; other CMake arguments are forwarded to that one build. Heap tracing and
diagnostic test modes default OFF for each script invocation. Enable heap tracing
explicitly with `-DMOONLIGHT_HEAP_TRACE=ON` in system mode.
Fresh direct CMake configurations also default to system; existing CMake cache
options persist unless explicitly overridden.
CMake prints the selected `Moonlight launch profile`. With Debug log enabled,
Settings logs `[Launch]` with the profile and source revision.

The system profile uses `gdc` packaging, a 64 MiB SELF budget, a 6 MiB newlib heap, a 10 MiB PAF
heap and PAF application mode. UNSAFE and the existing authority/settings remain.
These are the device-tested streaming allocations, not an established minimum.
PAF surface/text pools are 4/1 MiB after the initial 8/4 MiB configuration failed
with an 8 MiB DDR-main allocation request on startup with a game resident. The
smaller pools save 7 MiB in requested pool capacity. On `7e20e94`, the user verified
Main/Settings, launch without closing the Vita game, and resuming its existing session
on the tested device with the earlier 32 MiB browsing budget. That budget did not establish
streaming support; current system defaults and successful streaming evidence use 64 MiB.
Install the complete VPK through VitaShell, then launch from LiveArea, rather than
replacing only the SELF, so the changed launch metadata is promoted. Then test
opening Moonlight with a Vita game suspended and returning to that same game session.
Physical reservation defaults to zero; the decoder supplies its own explicit main-RAM arena.

The system profile bounds common-c transport thread stacks to 128 KiB (the ordinary
profile requests 1 MiB each). `[Thread]` logs report each thread name, stack bytes
and creation result. Thread creation and streaming passed the user's two longer
sessions and reconnect test; broader endurance/compatibility testing remains open.

The earlier device test passed control-thread creation but stopped at decoder initialization:
`0x80620840` is `SCE_VIDEODEC_ERROR_NOT_GAME_BUDGET`. The standard decoder API rejects
automatic allocation with the system application budget. The current prototype uses
the ABI recovered from the user's firmware dump: explicit library/decoder contexts
through a CodecEngine pool and contiguous uncached main-RAM output buffers. It logs
queried sizes and each allocation/init result. On `8b5d9a5` with a 64 MiB budget,
the user verified image, sound, controls and resuming the suspended Vita game after
the stream. This is one-device/game validation; broader compatibility remains open.

The initial 32 MiB browsing profile had only 648 KiB free before video setup.
The system-profile default is now the tested 64 MiB. Existing cached overrides
are preserved; if an older build directory still has 32768 cached, select the
tested value explicitly (maintainer command):

```bash
bash build.sh -DMOONLIGHT_SYSTEM_APP=ON -DMOONLIGHT_SYSTEM_MEMSIZE_KIB=65536 -DMOONLIGHT_SYSTEM_PHYCONT_KIB=0
```

Install the full VPK when changing the launch budget. The tested 960x544 stream
queried 5.5 MiB for the library and 8 MiB for decoder storage; the adapter allocated
a 15 MiB arena plus three 2 MiB output buffers. Decoder creation, GXM mapping,
1088 decoded frames, stream stop and deferred framebuffer release passed in the
reported run. Later user tests verified longer sessions, reconnect memory baselines,
Settings, Quick Actions and returning to the suspended game with tracing disabled.
Broader device/game, dialog/error-path and endurance coverage remains open.

Enable **Debug log** in Settings for `[Memory]` snapshots, including the actual
AppMgr mode and USER_RW/PHYCONT/CDRAM budgets. With the saved preference enabled,
the first snapshot is emitted when AppSettings loads during backend startup;
earlier bootstrap remains quiet. The prototype and tuning parameters are documented in
[docs/SYSTEM_APP_MODE_RESEARCH.md](docs/SYSTEM_APP_MODE_RESEARCH.md#prototype-on-codexsystem-app-mode).

Repeated common-c `Waiting for IDR/RFI frame` messages are limited to one per
second for each kind, with omitted-message totals reported after transport teardown.
IDR requests, recovery/drop-limit events and other logs remain visible. This limits
console traffic during recovery without changing the transport's recovery behavior.

The longer user run stopped after 2732 decoded frames with `Video Receive: malloc()
failed`. After teardown, newlib still reported 5591728 used bytes in its 6 MiB
heap, while USER_RW had 31412 KiB free. Allocation ownership and fragmentation
required investigation at that stage; the later root cause and retest follow below.
The subsequent diagnostic run identified repeated pthread thread-record allocations:
the custom entry point skipped VitaSDK's pthread constructor. Startup now explicitly
initializes pthread after newlib and verifies stable thread identity before entering
PAF. With the same 6 MiB heap, the user's retest completed 22270 decoded frames,
manual stop, reconnect and another 18008 frames without allocation failure or
crash. Newlib used returned to 96768 / 96936 bytes after the two stops, and final
USER_RW free was identical at 32952 KiB. This verifies the reported memory-failure
fix and one reconnect on the tested device; broader compatibility remains open.
The user also verified streaming/reconnect, Settings, Quick Actions and returning
to the suspended game with heap tracing OFF and the same budgets. The ordinary
profile also passed the user's launch, Settings, stream and reconnect smoke test
after the shared pthread-bootstrap fix. Fresh direct CMake configurations and
`build.sh` now default to the system profile. The 64 MiB budget
applies only when system mode is enabled.
An optional diagnostic build records allocation call sites (maintainer command):

```bash
bash build.sh -DMOONLIGHT_SYSTEM_APP=ON -DMOONLIGHT_SYSTEM_MEMSIZE_KIB=65536 -DMOONLIGHT_SYSTEM_PHYCONT_KIB=0 -DMOONLIGHT_SYSTEM_NEWLIB_KIB=6144 -DMOONLIGHT_HEAP_TRACE=ON
```

Install this VPK and enable **Debug log**. Keep its corresponding unstripped
`build/vita_moonlight_paf.elf`. Capture `[Heap]` lines before/after setup, at
`video-receive-oom`, and after stop; they report the twelve largest tracked live
allocation sites, failure size and an address anchor for matching the ELF.
This option defaults to OFF, adds about 136 KiB of fixed BSS metadata and allocation
tracking overhead, and does not increase the heap. It records references handled
by linker wrappers; libc-internal allocations/frees may bypass them. Counters for
dropped entries, unknown frees, replaced addresses and ambiguous zero-size realloc
results describe coverage limits. Tracked bytes are not a replacement for `mallinfo`.
Disable the diagnostic with `-DMOONLIGHT_HEAP_TRACE=OFF` after collecting the log.

CMake cache options persist for manual configurations; the script explicitly
selects one profile and defaults tracing OFF. To build the ordinary profile explicitly:

```bash
bash build.sh -DMOONLIGHT_SYSTEM_APP=OFF -DMOONLIGHT_HEAP_TRACE=OFF
```

Default system-profile outputs:

```
build/vita_moonlight_paf-system.elf
build/vita_moonlight_paf-system.self
build/vita_moonlight_paf-system.vpk
```

The build tree contains an unstripped `vita_moonlight_paf.elf` with debug symbols
for tools such as Vita Crash Dump GUI. The script copies it to the matching
profile-suffixed name above. Keep the ELF with its corresponding VPK when collecting
a crash dump. Script/manual builds also retain the original
`build/vita_moonlight_paf.{elf,self,vpk}` paths. The extensionless executable in
each build tree remains an internal input to VitaSDK packaging helpers.

Rebuild CXML manually:

```bash
bash build_cxml.sh
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
```

Install the generated VPK on the Vita (title ID `VLMP00001`). This checkout ships
`build.sh` and `build_cxml.sh`; the `dev-build-run.sh` deployment helper referenced
in older notes is absent. Deployment tooling is therefore a separate local setup.

LiveArea images under `sce_sys/` must be 8-bit indexed PNG (color type 3). A 24-bit or 32-bit PNG installs as far as 99% and then fails with `0x8010113D`. `icon0.png` is 128×128 with no alpha. `pic0.png` is 960×544. `livearea/contents/bg0.png` is 840×500. `startup.png` is 280×158. Startup and frame icons can use palette transparency (`tRNS`); local SDK LiveArea samples include transparent frame icons. Re-exporting these from a normal editor without quantizing them will break installation again.

`vita_create_vpk()` explicitly includes the LiveArea background, startup image/template
and three current manual pages (`001.png`–`003.png`); adding/removing files under `sce_sys/` also
requires updating this explicit packaging list. The deleted `004.png` and obsolete
`frame1.png`–`frame7.png` are no longer dependencies. Dynamic frames use explicitly
packaged indexed PNGs: `app_row.png` (472×48), `app.png` (128×128, displayed
at 32×32), `pc_card.png` (280×158), and the transparent `pc.png` (80×80).
`app_row.png` is a lossless indexed copy of Browser's `LA_window.png`. CMake
packages the existing `sce_sys/icon0.png` as `app.png`, without a second source
copy. Replacing `icon0.png` therefore affects both destinations; keep it 128×128,
8-bit indexed and opaque. `tools/generate_livearea_backdrops.py` uses Pillow to
derive the 280×158 PC card from the same Browser row with fixed 8 px corner/edge
caps; optional
`--browser-archive /path/to/sce_sys.7z`
imports the Browser row using 7z/Pillow with decoded-pixel equality verification.
The install template starts with native
“Moonlight” / “Open source game streaming client” text and no sample app/PC names
or purple placeholders. Install the full rebuilt VPK when changing these assets;
content revision is 12; frame3 is revision 7 and the other frames remain revision 6.
The installed display name is `Moonlight`. The original spotlight background has
no painted caption; native welcome text lives in frames. Current `gd`/`gdc`
categories skip the native top-left title. See the [LiveArea guide](docs/LIVEAREA.md)
for geometry, the shell-caption evidence and remaining device checks.
Packaging completeness and lossless palette conversion were
checked without an agent-run build. On 2026-10-21, the maintainer confirmed the
LiveArea assets appeared after deleting the old app and installing the full VPK
again. Installation over the existing app had retained the default appearance;
the cause and a reliable update-in-place procedure remain unverified.

The CXML build is fail-fast: if `psp2cxml-tool` is not available, the build stops instead of using an unrelated fallback resource.

## Runtime Validation

This branch adds [dynamic LiveArea text](docs/LIVEAREA.md): frame7 shows the last
successfully connected PC, and frames1–6 show its first six applications after
Apps retrieval. Native `SceLiveAreaUtil` publishes names asynchronously.
No promoter or direct shell-file/database writes are used.
The maintainer confirms changing labels on Vita. Populated app slots now have
the original translucent Browser row backdrops, 32×32 Moonlight markers and
left-aligned system text; Frame7 restores the transparent
PC icon and uses a card as wide as the gate startup image. With no Apps names,
native welcome text appears in the left column.
Frame7 now connects to its saved PC, and app frames connect, refresh Apps and
start the selected app ID through the existing PIN/progress/remote-Quit flow.
New frame targets must first be republished by connecting and retrieving Apps.

The maintainer replied “всё ок” on 2026-10-26 to the fresh VPK installation,
replacement icon/startup image, labels/card activation and closure/reboot
retention check following the PNG fixes at source revision `6e1a893`.
This is basic user-reported Vita acceptance; no package hash, runtime log or
per-profile results were supplied. Separate cold/resumed delivery, fresh welcome
defaults, short/empty lists and fault cases remain in the LiveArea guide.

The subsequent 2026-10-26 reply “всё ок” accepts the requested published-system-VPK
check: installation over the current app, Settings/saved-PC retention, connection
without another PIN, streaming and return to a suspended Vita game. Both v1.00
and v1.01 CI runs/releases succeeded. Download identities and the distinction
between that reply and the separate BMK update result are recorded in
[release evidence](docs/RELEASE.md#recorded-release-evidence-2026-10-26).

Non-build Python checks (Python 3 + pycparser) cover selected parser, pairing/trust,
host-store/list, event, lifecycle, input, video-size and LiveArea logic with mocked
platform/library calls. See [tests/README.md](tests/README.md) for the command,
current recorded count and limits. They do not compile or execute the application
or replace Vita tests. C/Expat fixtures also exist; maintainer compilation/execution
remains unverified.

Changes are validated primarily on real PS Vita hardware:

1. build the VPK/SELF;
2. deploy to the Vita;
3. reproduce the affected UI, discovery, pairing, or streaming path;
4. inspect the runtime log.

For streaming-related changes, verify at least connection setup, video/audio, input, and clean stream shutdown.

## Development Principles

- Reuse real upstream/legacy Moonlight logic where possible.
- Keep PAF UI independent from streaming implementation.
- Route application behavior through `MoonlightApp`, services, backend interfaces, and the legacy adapter.
- Deliver asynchronous backend events to PAF on the main thread.
- Prefer small, verifiable commits.
- Prefer real Vita system interaction patterns over invented PAF-only UX when a system-app equivalent is known.
- Do not replace the saved-host selection/action mode with long-press/context menus.
- Do not casually change persistent storage formats or paths without considering compatibility and migration.

## Development Roadmap

The current build environment and setup procedure are recorded in
[docs/BUILD_ENVIRONMENT.md](docs/BUILD_ENVIRONMENT.md). Clean CI setup, dependency rebuild and
both application-profile builds passed on `4076f15`; original local portlib binaries remain
unrecovered, and no byte-identical reproduction is claimed. Basic CI-package Vita smoke is
user-confirmed. [Installation](docs/INSTALL.md) and the
[release/versioning checklist](docs/RELEASE.md) are documented; remaining license
decisions, distribution materials and broader release/device coverage remain open.
System v1.00/v1.01 releases are published and the requested basic release-VPK
smoke is user-accepted; see the scoped evidence above.
Broader lifecycle/motion/security/error and release checks remain
open; ordinary API paths are not reopened merely because exhaustive validation is incomplete.
The canonical plan and completion criteria are in [`ROADMAP.md`](ROADMAP.md).

## Status

The project is an actively developed working Vita Moonlight frontend. Streaming is functional, but the UI, host-management behavior, lifecycle edge cases, and some device/input paths are still under active development.

As of 2026-10-22 the [client API audit](docs/SUNSHINE_API_AUDIT.md#6-completion-and-next-work)
is complete as an inventory/source comparison, with scoped Vita evidence for the normal client
flow. It is not full compatibility/security/release certification. Latest system build 5db31a9
logs typed wrong-PIN rejection, two separate Error 409 attempts, then successful pairing/Apps.
Remote self-unpair remains blocked by the absent Sunshine client operation under the agreed
no-admin-login constraint. Missing/unverified features and accepted limits are listed in the audit.

## License

The [licensing and attribution review](docs/LICENSING.md) records the Moonlight,
vendored-library and SDK terms, restored license texts, artwork provenance and
remaining release requirements. A top-level project license is still pending;
the remaining dependency/project-license and permission questions are recorded
in that review. Sony artwork permission work is outside the active plan by the
maintainer's decision; asset provenance is retained. The collected upstream
licenses do not grant rights to unrelated project files or assets.
