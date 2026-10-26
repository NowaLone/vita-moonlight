# Install and use Vita Moonlight PAF

This is the user setup guide for `NowaLone/vita-moonlight-paf`, title ID
`VLMP00001`, displayed as **Moonlight** on the Vita. Build instructions are in
[BUILD_ENVIRONMENT.md](BUILD_ENVIRONMENT.md). Release preparation is in
[RELEASE.md](RELEASE.md).

## Requirements and package choice

- A PS Vita with homebrew already enabled and permission to run **UNSAFE**
  applications. Where available, enable **Settings → HENkaku Settings → Enable
  Unsafe Homebrew**. Both Moonlight profiles require this for native system
  services; the system profile is not a replacement for enabling homebrew.
- [VitaShell](https://github.com/TheOfficialFloW/VitaShell) to transfer and install
  the VPK. A prebuilt VPK does not require VitaSDK or the PAF/CXML developer tools
  on the Vita.
- A PC running Sunshine with working capture, H.264 encoding, audio and the
  host-side input support appropriate to its OS. Follow the
  [official Sunshine setup guide](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html).
- The PC and Vita connected to the same reachable LAN for initial setup. Allow
  Sunshine through the host firewall; guest-network/client isolation can prevent
  discovery and connections. Internet streaming is not part of this setup guide.

Install **`vita_moonlight_paf-system.vpk`**, the default and distributed package.
This system profile has a 64 MiB budget and can open while a Vita game remains
suspended. Coexistence and streaming have scoped Vita evidence, not a guarantee
for every game/firmware. The suspended game is not running simultaneously. See
[system-profile evidence](SYSTEM_APP_MODE_RESEARCH.md).

An ordinary `-normal.vpk` remains available through an explicit local build
(`bash build.sh -DMOONLIGHT_SYSTEM_APP=OFF`); CI and Releases distribute system only.
Both profiles use **the same title ID** and replace one another. They are not two
independent installed applications. `.self` is a developer executable and `.elf`
is for matching crash/debug analysis; install the `.vpk` for normal use.

Earlier Settings/PS/stream checks document one **3.60 HENkaku Vita without
ioPlus**; ioPlus is not a required workaround. There is no established minimum
firmware or complete Vita/PS TV compatibility matrix. The 2026-10-26 LiveArea
acceptance did not supply firmware or separate profile results.

## Download and install

On 2026-10-26 the repository had no published GitHub Releases. Until a release
is published, use only a maintainer-designated successful
[Clean Vita build run](https://github.com/NowaLone/vita-moonlight-paf/actions),
download its `vita-moonlight-paf-<full-commit>` artifact and unpack the ZIP.
Record the run/commit and selected profile. An Actions artifact is a test build,
not automatically a validated release. Future releases belong on the
[project Releases page](https://github.com/NowaLone/vita-moonlight-paf/releases).

1. If updating, first follow the backup steps below. Fully close Moonlight.
2. Transfer the chosen complete `.vpk` using VitaShell's USB or FTP support to
   a folder on the Vita, for example `ux0:downloads/`.
3. In VitaShell, select that VPK and confirm installation, including the expected
   extended-permission prompt for this UNSAFE application.
4. Launch **Moonlight** from LiveArea. For the system profile, install the full
   system VPK so its launch metadata is applied; replacing only the SELF cannot
   establish the correct launch profile.
5. Check the icon/startup image, then open the bottom-right corner menu →
   **Settings** and return to Main. The app's settings use the native system UI.

## Prepare Sunshine and pair

1. Start Sunshine on the PC and finish its OS-specific capture/encoder/input
   setup. On that PC open its web UI, normally
   [https://localhost:47990](https://localhost:47990), and complete its local
   account setup. Sunshine uses a self-signed web-UI certificate; verify that
   you are opening your own local Sunshine service if the browser prompts.
   Add an application or Desktop in Sunshine's **Applications**.
2. Open Moonlight on the Vita. Main automatically discovers PCs while idle;
   saved PCs appear first, temporary discoveries below. Discovery pauses while
   Settings, manual entry, selection or a foreground connection is active.
3. Select the PC. If it does not appear, use Main's top-left PC-plus button and
   enter its LAN IPv4 address or hostname, such as `192.168.1.10`.
   You may supply `host:port`; the default GameStream HTTP port is **47989**.
   Enter an address, not a web URL or Sunshine's **47990** administration port.
   IPv6 literals are not supported; custom-port combinations need further testing.
4. When the Vita displays a PIN, keep that screen open. In Sunshine's web UI on
   the PC choose **PIN**, enter the Vita's number, and submit pairing. Cancel on
   the Vita if you want to abandon the attempt. The Sunshine administrator
   password is not entered into Moonlight.
5. After pairing, select an application from Apps to start streaming. A discovered
   PC is saved before connecting; a manually entered address is saved only after
   successful connection. A failed manual address should not create a saved PC.

The web UI/PIN steps follow
[Sunshine's pairing procedure](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html#configuration);
its [port setting](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2configuration.html#port)
controls a family of ports, not just the administrative web page.

## Stream, stop and reconnect

Settings are available from Main's corner menu → **Settings**. Fresh streaming
defaults are **1280×720, 60 FPS, 5000 kbit/s**; existing settings may differ.
This client requests **H.264 video and stereo audio**. It does not request
HEVC, AV1, HDR or surround audio. A resolution/FPS option is not a performance
guarantee. Reduce FPS/bitrate or resolution if the connection or decoder struggles.

For the first test, leave **Enable PS button capture** enabled (the default).
During streaming, **double-press PS** to stop the stream and return to the app
list. A short single press can be sent to the host; holding PS is reserved for
the Vita's Quick Actions. An ordinary stop/disconnect does not quit the PC game.
Select it again to reconnect/resume.

If a different application is already active on the host, Moonlight asks whether
to quit it before launching your selection. Choose **Yes** only when that is
intended; **No** preserves the existing host application.

Front touchscreen mode and gyro are selectable in Settings. Touchscreen mode
defaults to **Off**; enable the desired mode explicitly. Motion and the broader
device/game compatibility matrix remain incomplete. The optional statistics
overlay is diagnostic; its PAF submission rate is not a physical display-rate
measurement.

Connecting and obtaining Apps publishes the last PC and first six applications
to LiveArea. Tap the PC card to connect/open Apps, or an app card to connect and
launch that app. LiveArea is the last successful snapshot, not a background
network refresh after Moonlight closes. Basic card launch and closure/reboot
retention were accepted on Vita on 2026-10-26; edge cases are in
[LIVEAREA.md](LIVEAREA.md).

## Update, switch profile and preserve pairing

1. Fully close Moonlight and back up the **whole** `ux0:data/moonlight/` directory,
   including `client/`, every host's `device.ini` and `server.pem`, and any input
   mapping file. The host store can fall back to `ux0:moonlight/` or
   `uma0:data/moonlight/` when earlier paths are unavailable: preserve the active
   store there too if your installation uses it. Do not move stores as an update step.
2. Note your Settings values separately. AppSettings storage is separate from
   the host/client directory; that directory backup alone does not back it up.
   The backup contains the Vita's private pairing identity: keep it private.
3. Install the full newer **`vita_moonlight_paf-system.vpk`** through VitaShell.
   An explicitly built normal profile can be installed the same way when intended.
   Keep the data directories in place. Neither switching profiles nor
   routine updating calls for deleting client identity or server pins.
4. Reopen Moonlight, check Settings, connect to the saved PC and verify Apps,
   stream stop/reconnect and LiveArea. Changed LiveArea targets are published
   after a successful connection/Apps retrieval. Data/Settings retention during
   updates is a release check, not guaranteed solely by using the same title ID.

There is no built-in VPK installer. Packages include `sce_sys/homebrew_update.ini`
pointing a compatible external shell plugin to the latest published Release's
`VLMP00001-ver.xml` feed. This does not install the plugin, and the blue LiveArea
refresh action alone cannot install a GitHub build. The maintainer confirmed
the system v1.00 → v1.01 update with **BMK-Studio HomebrewUpdate on firmware
3.60** on 2026-10-26. The tested path used the existing release VPK filename.
For that firmware, use BMK's plugin rather than zm2283145's 3.65-specific
implementation. Follow [BMK's installation instructions](https://github.com/BMK-Studio/HomeBrewUpdate#installation),
disable the old update plugin and reboot before testing its replacement;
do not enable both together. This scoped result does not verify other firmware,
plugin coexistence or Settings/identity retention. VitaShell remains the manual
update procedure above; see [the test evidence and limits](APP_UPDATE_RESEARCH.md).
NeoVitaDB publication is separate; see [APP_UPDATE_RESEARCH.md](APP_UPDATE_RESEARCH.md).
The original xyzz Vita Moonlight is a different application; this project does
not migrate its old per-host credentials. Pair this client again when moving over.

## Troubleshooting and known limits

- **VPK installation error `0x8010113D`:** use a freshly rebuilt complete package
  containing the icon/startup PNG fixes, rather than an older VPK or a SELF-only
  replacement. Supply the package hash/profile if it still fails. Fresh install
  was accepted after source revision `6e1a893`.
- **Old icon/LiveArea artwork after an update:** check that you installed the full
  intended VPK. Earlier update-in-place installs retained old artwork; a general
  cache-refresh fix is not established. Before considering a manual reinstall,
  make the backups above and record Settings. Do not edit the shell database.
- **PC absent/offline:** check Sunshine, its LAN address, Wi-Fi isolation and
  firewall, then try manual IPv4 entry. The saved-PC dot only reports a recent TCP
  probe; it does not prove pairing, host idleness or streaming readiness.
- **Pairing failure/409:** finish or cancel the current PIN attempt before starting
  another. A host may still have an earlier pending pairing attempt. Read the
  specific error; transport or security failures are not necessarily a wrong PIN.
- **Saved certificate changed/unreadable:** first confirm on the PC whether a
  reinstall/certificate change was expected. For an intentional trust reset,
  delete that PC through Main → corner menu → **Delete**, add it again and pair.
  Do not disable certificate verification. Local Delete does not revoke the Vita
  on Sunshine; remove that paired client in Sunshine separately if revoking access.
- **Need diagnostics:** enable **Debug log** in Settings and collect the psp2shell
  console output, plus Sunshine's Troubleshooting log. Moonlight writes no log
  file. Include source revision/package SHA256, profile, firmware, Sunshine
  version/OS, stream settings and reproduction steps; exclude private credentials.

Remaining discovery/UI, motion, storage/trust faults, custom-port/encryption,
endurance and compatibility checks are tracked in [ROADMAP.md](../ROADMAP.md)
and the [client API audit](SUNSHINE_API_AUDIT.md). Existing scoped Vita results
do not establish support for every Sunshine/GameStream server version.
