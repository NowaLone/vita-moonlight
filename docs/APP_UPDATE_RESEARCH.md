# Application updates and the LiveArea toolbar

Research date: 2026-10-25. Project source inspected at `f54dda4` on
`codex/livearea-dynamic-frames`. This records feasibility and implementation
choices; it does not implement an updater or authorize installing a shell plugin.

## Finding

GitHub Releases can host Moonlight PAF updates. NeoVitaDB can index those releases
and install their VPKs. A homebrew update workflow in the native LiveArea toolbar
is also possible through an additional SceShell plugin. No supported app-local
setting was found that redirects the existing blue refresh button to a GitHub VPK.

The lowest-effort distribution path is published GitHub releases plus a NeoVitaDB
entry for an explicitly chosen profile. Native toolbar integration is a separate,
optional compatibility decision, not a prerequisite for GitHub distribution.

## Which button is in the screenshot?

The blue circular arrows are **Refresh LiveArea Screen**. Sony distinguishes this
from **Update**, the separate application-update action shown when a newer
application version is available. Refresh can precede discovery of the latter;
it does not itself mean installing a new executable.
[Sony screen guide](https://manuals.playstation.net/document/en/psvita/basic/screens.html),
[Sony PS TV quick-start guide, p. 9](https://www.playstation.com/content/dam/global_pdc/en/corporate/support/manuals/pstv-docs/VTE-1016_PS%20TV_QSG%24en.pdf).

The supplied local SceShell disassembly independently shows a Sony update URL
assembled around addresses `0x812a9ef0`–`0x812a9fa2`:
`https://gs-sec.ww.<env>.dl.playstation.net/pl/<env>/<TITLEID>/<hash>/<TITLEID>-ver.xml`.
This is static evidence from the supplied binary, not a cross-firmware runtime
test. The existing annotation was read at
`/tmp/livearea-shell-analysis/annotated.txt`, approximately lines 986391–986443;
that temporary file is not shipped with this repository.

The [VitaSDK LiveArea API](https://github.com/vitasdk/vita-headers/blob/master/include/psp2/livearea.h)
and our [small binding](../include/platform/livearea.h) expose content/frame
publication, not a toolbar-click callback or a binary-update source setting.
Our [LiveAreaService](../src/services/livearea_service.cpp) publishes PC/app
frames while Moonlight runs. It cannot install a newer Moonlight VPK through
those calls. The `"01.00"` passed to `sceLiveAreaUpdateFrameAsync` is the XML
**format version**, independent of the application SFO version.

## Existing native-toolbar implementations

### Open implementation: VitaHomebrewUpdate

[VitaHomebrewUpdate v1.0.1](https://github.com/zm2283145/VitaHomebrewUpdate/releases/tag/v1.0.1)
was published on 2026-09-25 with a shell-plugin binary, source archive and client
library. The inspected source revision is
`9575967122195c559971594f66cad0d6471bb18b`.

Its per-title `sce_sys/homebrew_update.ini` supplies the title ID and a stable
manifest URL. An XML feed on GitHub raw hosting can reference a versioned tagged
GitHub Release VPK and change information. The feed supplies version, size,
SHA-1 and Content ID. The plugin handles BGDL, package checks, staging and install.
[Integration contract](https://github.com/zm2283145/VitaHomebrewUpdate/blob/9575967122195c559971594f66cad0d6471bb18b/README.md).

This requires a taiHEN plugin under `*main`. The implementation hooks SceShell
HTTP/update-controller/launch paths, substitutes the per-title update URL, then
promotes the verified extracted package. It is not evidence that unmodified
Sony update code accepts an arbitrary VPK URL from our LiveArea XML.
[Implementation](https://github.com/zm2283145/VitaHomebrewUpdate/blob/9575967122195c559971594f66cad0d6471bb18b/service-plugin/main.c).

The author only claims hardware-proven scope for **retail firmware 3.65**. Source
checks the SceShell NID `0x5549BF1F` and uses firmware-specific offsets. The release
also reports confirmed incompatibility with VitaDB Downloader's
`vdb_daemon.suprx`: shell locks, LiveArea corruption and network instability.
Compatibility with the NeoVitaDB daemon must not be inferred from its forked
origin or assumed safe without separate evidence.
[Release scope and limitations](https://github.com/zm2283145/VitaHomebrewUpdate/blob/9575967122195c559971594f66cad0d6471bb18b/docs/RELEASE_NOTES_v1.0.1.md).

### Binary alternative: BMK HomeBrewUpdate

[BMK-Studio/HomeBrewUpdate 1.6](https://github.com/BMK-Studio/HomeBrewUpdate/releases/tag/1.6)
was published on 2026-08-28 with a plugin and developer client. The inspected
public source tree contains only README.md. Its claimed LiveArea integration
and broader firmware support therefore cannot be verified from implementation
source. It is an available binary alternative, not an audited project dependency.

## NeoVitaDB distribution and updates

Inspected snapshots:

- [Downloader v2.9.1](https://github.com/robin994/NeoVitaDB-Downloader/releases/tag/v2.9.1),
  source `2fe6f6618f77cdd8d0e10b4c240e3865e1214085`.
- [Production catalog](https://github.com/robin994/NeoVitaDB-Catalog/tree/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8),
  source `ac0c767b910c6f39e483f326107ca6c9c4b3a9a8`.
- [Test catalog](https://github.com/robin994/NeoVitaDB-Catalog-Test/tree/048c717623f681dfa7c56cac52157459e7dadab0),
  source `048c717623f681dfa7c56cac52157459e7dadab0`.

NeoVitaDB stores metadata; release binaries remain on the author's GitHub.
New entries first go through a PR against **NeoVitaDB-Catalog-Test**, with one
`apps/vita/` JSON and a 128×128 PNG icon. The catalog maintainer later promotes
accepted entries to production. The entry needs a permanent numeric catalog ID,
our `VLMP00001` title ID, repository and a precise release asset selector.
[Contribution process](https://github.com/robin994/NeoVitaDB-Catalog/blob/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8/README.md#adding-your-homebrew),
[entry schema](https://github.com/robin994/NeoVitaDB-Catalog/blob/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8/schema/app.schema.json).

The resolver takes a release and the first asset matching its glob. For this
project, use an exact name such as `vita_moonlight_paf-normal.vpk` or its system
counterpart, not `*.vpk`. Two profiles share `VLMP00001`; the catalog has no
automatic installed-profile selection. Displayed version comes from GitHub's
release tag. Installed-state detection compares the MD5 of `eboot.bin` (or its
local hash cache), with extra data checks for selected engines. Consequently,
a resource-only change with an identical executable may not be detected.
[Asset selection and hashes](https://github.com/robin994/NeoVitaDB-Catalog/blob/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8/tools/build_catalog.py#L143-L269),
[installed-state check](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/source/database.cpp#L173-L228).

The inspected catalogs did not contain a `VLMP00001` entry. Their existing
[Vita Moonlight record](https://github.com/robin994/NeoVitaDB-Catalog/blob/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8/apps/vita/0076-vita-moonlight.json)
is `xyzz/vita-moonlight`, title ID `XYZZ00002`, not this project.

The optional daemon sends a native `LAUPDATE` notification naming the updated
title, targeting client `NEOVITADB`, with the **numeric catalog ID** as its launch
argument. This supplies notification → Downloader → installation. No hook of
the blue refresh button was found; the notification type alone does not prove
that button has been redirected.
[Notification implementation](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/daemon/main.c#L98-L115).

The client's on-demand path reads its local daemon-generated `NeoVitaDB.json`,
matches that numeric ID and installs through Promoter. A launch with the title
ID `VLMP00001` is not the same contract. A missing/stale daemon cache also limits
this path; no public `neovitadb://update/<titleid>` URI was found.
[Argument handling](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/source/main.cpp#L857-L865),
[cache input](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/source/main.cpp#L1188-L1203),
[installation path](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/source/main.cpp#L2996-L3035).

Two implementation limits matter when planning integration:

- The catalog README promises a six-hour refresh, but the inspected production
  [workflow](https://github.com/robin994/NeoVitaDB-Catalog/blob/ac0c767b910c6f39e483f326107ca6c9c4b3a9a8/.github/workflows/build.yml#L1-L12)
  schedules Sunday 03:17 UTC, plus push/manual runs. Do not promise a six-hour SLA.
- Downloader disables TLS hostname and peer verification in its
  [curl configuration](https://github.com/robin994/NeoVitaDB-Downloader/blob/2fe6f6618f77cdd8d0e10b4c240e3865e1214085/source/network.cpp#L177-L191).
  Its MD5 installed-state check is not a package signature. Reusing Downloader
  as an external installer is a trust decision; copying these settings into
  our own updater would remove required transport verification.

## What Moonlight PAF needs before release updates

Our [CMake file](../CMakeLists.txt) currently packages both launch profiles as
`VLMP00001`, SFO version `01.00`, with different `gd`/`gdc` categories and SELF
attributes. [build.sh](../build.sh) already gives the packages stable separate
names. The [CI workflow](../.github/workflows/build.yml) uploads artifacts with
14-day retention; it does not publish Releases. The public
[release collection](https://api.github.com/repos/NowaLone/vita-moonlight-paf/releases)
returned no releases on the research date.

Recommended order, not an implementation commitment:

1. Define release versions and publish tagged VPK assets, size and SHA-256.
   Decide which profile NeoVitaDB should distribute. A title-ID match alone
   cannot preserve normal/system; per-profile plugin feeds or a profile-aware
   in-app selector are needed when supporting both channels.
2. Submit the selected package to the NeoVitaDB test catalog. This can enable
   external installation/updates without adding a custom updater to Moonlight.
3. If native LiveArea update UX is required, evaluate an existing optional
   plugin against the actual firmware and installed plugins. Do not create a
   new shell-hook implementation merely to host releases on GitHub.
4. If updates must work without a catalog client or shell plugin, add an
   in-app check/download and explicit installer handoff. GitHub offers public
   [latest-release metadata](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
   and [stable release-asset links](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases).
   No embedded account token is necessary for public downloads.

A complete custom installer is more work than checking for a version. It must
verify transport, size/hash, SFO identity/version/profile and extraction paths,
stage outside the running installation, then hand off for installation/restart.
VitaShell provides an existing example of a separate
[updater application](https://github.com/TheOfficialFloW/VitaShell/blob/master/updater/main.c).
Its process-destruction behavior is not suitable to copy blindly into our
system profile, which may coexist with a suspended game.

Our existing curl/OpenSSL dependencies can support release downloads, but the
GameStream handle in [legacy_gamestream.c](../src/backend/legacy/legacy_gamestream.c)
uses paired-server certificate pinning/client credentials and disables redirects
and hostname checks. It is not a general GitHub download handle. Use separate
normal HTTPS verification for an updater, preserving the GameStream trust path.

Installation must leave `ux0:data/moonlight/` client identity, saved PCs and
server pins untouched. AppSettings retention, normal/system preservation,
suspended-game coexistence, download interruption, low space, install errors and
restart behavior remain Vita validation requirements for whichever path is chosen.

## Validation scope

This investigation read project source, existing local shell annotations, public
source and GitHub release metadata. No application/resource compilation,
packaging, CI dispatch, deployment, plugin installation, device mutation or Vita
update test was performed. No updater behavior is marked implemented or
hardware-verified. This document adds no release task to the active roadmap.
