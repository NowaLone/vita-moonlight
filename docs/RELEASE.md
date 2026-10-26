# Release procedure

Pushing a version tag starts **Clean Vita build** and automatically publishes a
system-profile release after successful checks/build. There is no manual workflow
trigger or release-mode input. The agent does not run builds, package/deploy the
application, dispatch workflows or publish releases while implementing it.
Installation is documented in
[INSTALL.md](INSTALL.md); environment/source pins are in
[BUILD_ENVIRONMENT.md](BUILD_ENVIRONMENT.md).

## Version and artifact convention

Use release tags **`vMAJOR.MINOR`**, with a two-digit minor component: for example
`v1.00`, then `v1.01`. Use the matching two-digit Vita `APP_VER` in the root
`MOONLIGHT_APP_VERSION` CMake setting: `01.00`, then `01.01`.
Increment minor for subsequent fixes/features and major for a new major line;
both fields must fit the Vita `NN.NN` form. This keeps one visible release
number rather than introducing a third component the package does not carry.

This is a Vita two-component version, not three-component SemVer. The workflow
accepts canonical tags such as `v1.01`, derives `01.01` and compares numeric components.
`01.99` is followed by `02.00`; `1.0.1`, suffixes and unpadded package versions
are rejected. The package's separate SFO `VERSION` is explicitly set to the
same value as `APP_VER` as a project policy. VitaSDK's `vita_create_vpk(VERSION)`
otherwise only sets APP_VER; generator defaults differ between SDK revisions.
[VitaSDK packaging helper](https://github.com/vitasdk/vita-toolchain/blob/008ddc2d7fd4bd16631d1e49cacf308de6f545f1/cmake_toolchain/vita.cmake#L383-L390),
[SFO string fields](https://github.com/vitasdk/vita-toolchain/blob/008ddc2d7fd4bd16631d1e49cacf308de6f545f1/src/vita-mksfoex/vita-mksfoex.c#L68-L86).

Prepare candidates locally before pushing the release tag. Candidate builds may
share APP_VER, so distinguish them by full commit and hashes; native version-based
updates do not distinguish equal-version candidates. Tag pushes publish stable
releases automatically, without a separate draft/build-only option. Prerelease,
three-component and padded-major tags (`v1.01-rc.1`, `v1.0.1`, `v01.01`) are rejected.
Never replace a published tag/asset with different bytes; a changed published
package needs a new version.

The local source default remains **`01.00`**. Tag **`v1.01`** selects **`01.01`**,
which is newer than existing 01.00 installations. Actions passes the tag-derived
value into CMake, then checks SFO against the update XML. Releases v1.00 and
v1.01 were published through Actions on 2026-10-26; the maintainer reports a
successful Vita update between them. `"01.00"` in LiveArea API calls is an XML
format version, and template content/frame revisions are resource revisions;
neither is the application version.
To reproduce a chosen version locally, pass it explicitly, for example
`bash build.sh -DMOONLIGHT_APP_VERSION=01.01`; checking out a release tag alone
does not override the local CMake default/cache.

### Content identity

`TITLE_ID=VLMP00001` identifies the application. Its stable `CONTENT_ID` is now
explicitly **`EP9000-VLMP00001_00-0000000000000000`** in SFO and the update XML.
This is the conventional 36-character package/content identifier, using the
same value [VitaShell supplies when CONTENT_ID is empty](https://github.com/TheOfficialFloW/VitaShell/blob/81af70971ba18b8ce86215b04180f1e3d21cdfc9/package_installer.c#L240-L264).
It participates in package/license metadata and the plugin's identity checks;
it is not a signature, credential or Sony registration. Do not change it per
release, version or profile. TITLE_ID and the data paths remain unchanged.
Update from an older empty-CONTENT_ID package, including AppSettings retention,
still needs Vita testing.

Keep these filenames inside every versioned release:

```text
vita_moonlight_paf-system.vpk
vita_moonlight_paf-system.self
vita_moonlight_paf-system.elf
VLMP00001-ver.xml
VLMP00001-changeinfo.xml
SHA256SUMS
vita-moonlight-paf-source.tar.gz
vita-moonlight-paf-build-evidence.tar.gz
```

The system VPK is the user download. SELF/debug ELF must come from the **same build**
as the VPK. Normal is an optional local build only (`bash build.sh
-DMOONLIGHT_SYSTEM_APP=OFF`), omitted from Actions/releases and the plugin feed.
It still shares title ID **`VLMP00001`**, so installing it replaces system.
The release tag/commit and SHA256 identify the bytes; a filename alone does not.

Also retain final license/notice materials and exact corresponding-source and
dependency inputs. The workflow includes tracked source
and initialized submodules in its source archive, and CI evidence including
rebuilt dependency packages. These bundles do not resolve the remaining license
decisions or automatically supply every required corresponding-source/relinking
material. Do not include private Vita data, keys, certificates or local
deployment addresses in any bundle.

## Actions publication

Create a version tag on the intended source commit (which must contain this
workflow), then push that tag, for example:

```bash
git tag -a v1.01 -m "Moonlight v1.01"
git push origin v1.01
```

Lightweight tags (`git tag v1.01`) work too. The workflow only triggers on pushed
tags matching `v*.*`; strict tag/version validation runs before SDK setup. There
is no manual trigger; branch pushes, PRs and tag deletion do not start a release build. Tagging a
commit is the maintainer's publication action; it does not require a separate
Run workflow or Publish Release click.

The checked-out commit is fixed throughout both jobs. The existing remote tag
must resolve to that commit, including through annotated tags. Only publication
receives `contents:write`; it never creates, rewrites or deletes Git refs. Existing
releases and versions not newer than Latest are rejected before building and
again before publication. Publication jobs are serialized.

After the build, Actions creates a temporary draft, uploads/verifies every asset,
rechecks the tag and then publishes the complete release as Latest. Upload or
verification failure leaves the draft for maintainer inspection; no asset is
overwritten. A moved/deleted tag prevents publication. An existing release,
including an unfinished draft, is not silently replaced on retry.

Every successful build produces `moonlight-release-<commit>-<attempt>` containing
the full asset set above. The usual application/debug and evidence artifacts
remain available, all with 14-day Actions retention. Published release assets
provide durable downloads outside that artifact retention period.

The system VPK includes `sce_sys/homebrew_update.ini` pointing to
`https://github.com/NowaLone/vita-moonlight-paf/releases/latest/download/VLMP00001-ver.xml`.
The XML references the VPK and CDATA changeinfo at that exact versioned release,
so a newer publication cannot mix manifests and payloads. Only publishing the
complete release changes the Latest feed; drafts do not. Package size/SHA-1 and
Title ID/APP_VER/CONTENT_ID match the VPK; SHA256SUMS covers all downloadable
payloads. [Stable GitHub asset links](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases).
Normal intentionally omits this INI to avoid conversion to system through the feed.

An external update plugin is not installed automatically. On 2026-10-26 the
maintainer confirmed the system (`gdc`) v1.00 → v1.01 update on firmware 3.60
with **BMK-Studio HomebrewUpdate**, using the existing release filenames.
zm2283145's VitaHomebrewUpdate failed its required firmware hook gates on that
device. Exact evidence, limits and the distinction between the two plugins
are recorded in [APP_UPDATE_RESEARCH.md](APP_UPDATE_RESEARCH.md). The separate
release-smoke reply below accepts Settings/saved-PC retention and reconnect
without a new PIN; it does not identify the installation method for that check.

## Recorded release evidence (2026-10-26)

GitHub release metadata and completed Actions runs identify these system VPKs:

- [v1.00](https://github.com/NowaLone/vita-moonlight-paf/releases/tag/v1.00),
  source `723a11341bf3e28d1dd47a4ce2a190a40d0330d3`,
  [successful run 40308203654](https://github.com/NowaLone/vita-moonlight-paf/actions/runs/40308203654).
  `vita_moonlight_paf-system.vpk`: 2694007 bytes, SHA256
  `b96ef7a36afa51376e337b69441ca18b3e0e45154bdb3c895085cdfc9a484dbf`.
- [v1.01](https://github.com/NowaLone/vita-moonlight-paf/releases/tag/v1.01),
  source `d696bc8f0d7230a7ff756255fbd9f94e4e103c6d`,
  [successful run 40310089489](https://github.com/NowaLone/vita-moonlight-paf/actions/runs/40310089489).
  `vita_moonlight_paf-system.vpk`: 2694011 bytes, SHA256
  `d6d39ebaee54176e94aec74514136ba5495c955e484709b11cb86c456375f48e`.

The maintainer replied **“всё ок”** to the requested published-system-VPK check:
installation over the current app, Settings and saved-PC retention, connection
without another PIN, streaming and return to the suspended Vita game. This is
user-reported acceptance of those basic cases; the agent did not build/install
or run the packages. The request named v1.00; the reply did not specify a tested
tag/hash, installation method, resident game or new log. The download identities
above are verified release metadata, not a measurement of the installed file.
Keep the separately recorded BMK v1.00 → v1.01 update result distinct. The
remaining fault/motion/compatibility cases and the complete checklist below are
not claimed complete; do not reopen the accepted basic cases without a regression.

## Candidate preparation

- [ ] Select the candidate version and exact source commit. Review the changes
  since the last accepted baseline and confirm that the worktree/submodules are
  the intended state. Select the tag corresponding to the intended package version.
- [ ] Run the non-build source checks from [tests/README.md](../tests/README.md)
  and record the actual output/count for that commit. A historical count is not
  a current test result.
- [ ] Resolve/record the remaining licensing decisions and include the required
  notices and corresponding-source/relinking materials described in
  [LICENSING.md](LICENSING.md). Sony artwork permission work is outside the agreed
  plan; an OpenSSL migration is not an agreed task. Do not silently mark these
  recorded scope decisions as permission grants or a completed license selection.
- [ ] Update [INSTALL.md](INSTALL.md), known limitations and release notes for
  the resulting behavior. State the supported/tested scope instead of claiming
  an untested minimum firmware or universal host compatibility.
- [ ] Check release configuration: `MOONLIGHT_HEAP_TRACE=OFF` and all five
  `MOONLIGHT_{DISCONNECT,ACTIVE_DISCONNECT,PENDING_DISCONNECT,HTTP_DISCONNECT,STARTUP_DISCONNECT}_TEST`
  options OFF. Do not ship an injected-disconnect diagnostic package. Use the
  documented default system memory configuration unless explicitly tested.

## Maintainer build and package inspection

- [ ] Before pushing a release tag, the maintainer builds/tests the candidate
  locally with the explicit version. Pushing the tag starts the
  [workflow](../.github/workflows/build.yml), which rebuilds pinned SDK inputs,
  portlibs, PAF/CXML and the system profile, then publishes automatically.
  The resulting CI VPK still needs its own hardware acceptance; do not mistake
  publication or a successful build for a Vita test result.
- [ ] Confirm the successful run's resolved commit and source-check results;
  retain `moonlight-release-<commit>-<attempt>` and the application/debug and
  build-evidence artifacts. They currently expire after
  **14 days**. Preserve the release evidence before that deadline.
- [ ] Verify the three application files against the run's `application.sha256`
  and the complete release set against `SHA256SUMS`.
  Inspect the VPK as a ZIP archive without rebuilding: check the intended
  `param.sfo` title/version/Content ID/category (`gdc`), update INI, full RCO,
  AppSettings resources, LiveArea template/images and manual, and correct
  profile executable. `icon0.png` must be opaque indexed 128×128; packaged
  LiveArea PNGs must meet the checks in `test_livearea.py`.
- [ ] Confirm the final notices/source materials are actually present in the
  intended distribution. The current workflow/CMake manifest does not package
  the license bundle automatically; a source document alone is not that step.
- [ ] Prepare the final downloads and `SHA256SUMS`. Preserve original build
  hashes/evidence alongside any distribution additions. Any code/resource or
  executable change requires a new candidate build and appropriate validation.

## Vita release-candidate check

Test the actual hashed system VPK above, not a later local SELF. Any optional
normal-build check is separate from release acceptance. Preserve
the data/Settings backup described in the install guide before installation tests.

- [ ] **Install/update:** verify fresh VPK installation, icon/startup/default
  LiveArea and startup. Exercise update from the previous supported package when
  one exists, including host/client identity and Settings retention. Record
  reinstall-only or stale-artwork behavior rather than promising update-in-place.
- [ ] **Main and Settings:** saved/discovered/manual PC connection, Delete
  selection/OK/Cancel, responsive discovery pause/resume, Settings changes and
  restart persistence. Include an empty-list state.
- [ ] **Pairing/Apps:** a new PIN pair, cancel/error return, app listing, restart
  and reconnect to the saved paired host without another PIN. Do not reset or
  publish the global client identity just to collect a test result.
- [ ] **Stream:** video, audible audio, controller and enabled touch mode, PS
  double-press stop, Quick Actions, return to Apps and reconnect. Confirm the
  remote-Quit Yes/No flow when another host application is active.
- [ ] **LiveArea:** labels/card activation and closure/reboot retention; apply
  the remaining short/empty/stale/busy/cancel cases from [LIVEAREA.md](LIVEAREA.md)
  relevant to the release's claims. Do not assume an earlier basic check covers
  every frame/event case.
- [ ] **System profile:** open Moonlight with a Vita game suspended, stream/stop
  and return to the same game session. Record the game/firmware and any failure;
  the normal profile has no coexistence promise.
- [ ] **Limits:** review outstanding device/fault/motion/endurance items in
  [ROADMAP.md](../ROADMAP.md). Record tested cases and explicitly deferred scope;
  do not tick unrelated checks from a normal-path success.

Earlier evidence remains useful: clean CI at `4076f15` and the 2026-10-26 basic
LiveArea acceptance following `6e1a893`. Neither identifies the future release
candidate's exact packages/profile results or replaces its release check.

## Release record and publication

Keep this record with the release notes/evidence, filling actual values:

```text
Tag / package APP_VER:
Full source commit / submodule revisions:
CI run URL / attempt:
Artifact filenames / SHA256SUMS:
Source and license/notice bundle locations:
Vita model / firmware / homebrew / relevant plugins:
System profile: tested cases, resident Vita game, result, log/evidence:
PC OS / Sunshine version / capture-encoder / input support:
Resolution / FPS / bitrate / enabled input features:
Update-from version / identity and Settings retention result:
Known limits / deferred checks / rollback package:
```

- [ ] Push the selected version tag and confirm its successful Actions run
  published the expected source commit and exact downloads. Retain source/notices
  and the completed record alongside the release.
- [ ] Link the install guide, changes, known limitations and
  previous validated package for rollback. Preserve backups when rolling back;
  compatibility with data written by a later version must not be assumed.
- [ ] If subsequently submitting to NeoVitaDB, select the exact
  `vita_moonlight_paf-system.vpk` asset, not `*.vpk`. Follow the existing
  [update research](APP_UPDATE_RESEARCH.md); no catalog submission, built-in
  updater or shell-plugin installation is performed by this workflow.
