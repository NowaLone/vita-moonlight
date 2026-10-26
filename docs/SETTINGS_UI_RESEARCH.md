# Settings header and Wi-Fi indicators

Read-only resource/ELF investigation, 2026-10-23. This supplements the screenshot
measurements in [UI.md](UI.md); it does not change Moonlight's interface. **[code]**
below means decoded RCO or inspected ARM instructions, not native execution.

## Supplied files and method

The maintainer supplied these firmware files; their exact firmware version was not
established. Do not generalize the hashes/layout to every firmware:

- `system_settings_main.rco`, SHA-256
  `b5dcc4cd3f7c3c0705989dacc4bf5668c7038418a918a483f80de038bc9b02bf`.
- `system_settings_plugin.rco`, SHA-256
  `1a460c4ea1b58d38d3289b96211a6c88ec7da56495a84f6a1b3dddff4bdddd4e`.
- Settings `eboot.bin.elf`, SHA-256
  `e1a80dfa535e6d5b6eed80ef3fb559bd099cec3fbc1152e93a2adcf49913f788`.
- `wifi_settings_plugin.rco`, SHA-256
  `564c0ba09f9ecdf7fd7bde1005ff481997f9c8cebfa1709e0a8f3e016dea0f37`.
- Previously supplied `common_resource.rco`, SHA-256
  `6ee58e58d1e78fecd99ea93e585c81efde3e940e3e0ca5cec4e64ba7cacdc806`.
- Screenshot `2026-10-23-022829.jpg`, 960 x 544.

RCO tree/attribute/file tables were decoded without compiling resources. Compressed
payloads were decompressed with zlib; GIM palette pixels and alpha were exported to
PNG. Main/plugin/Wi-Fi contain respectively 221/40/265 nodes and 17/17/18 textures.
Unknown names below are written as `hash_XXXXXXXX`; those are descriptive labels
for original ID hashes, not recovered Sony resource names. RCO node offsets are
relative to the tree, whose file offset is `0x50` in these files.

The ELF identifies itself as `SceSettings`. Its first LOAD maps file `0xe0` to
`0x81000000` (size `0x2938dc`); its second LOAD maps file `0x293a00` to
`0x81294000`. Code addresses below are virtual addresses in this supplied image.
Import NIDs were matched against the installed VitaSDK/PAF databases; unresolved
imports retain numeric NIDs. No builds, module execution or hardware tests.

## Header: the exact resource is local to Settings

### LiveArea caption recheck, 2026-10-24

The maintainer asked whether the green top-left `Settings` caption on LiveArea
is present in these two RCOs. Their hashes still match the inputs above. A fresh
tree/attribute decode finds 221 nodes in main (24 templates, nine text widgets,
nine text styles, 17 textures) and 40 in plugin (string/texture tables and 17
textures, no templates or text widgets). All nine main text styles specify
opaque white. The `main_page_title_text`/`style_text_header` composition below
is the centred, bold 32 px in-app header; it does not match the thin green
caption on the shell's LiveArea. No matching LiveArea heading element was found
in either supplied RCO. This does not rule out runtime-created elements or a
resource elsewhere in SceShell. The two app RCOs do not establish the shell's
title-eligibility rules. No RCO compiler, executable or Vita call was run.

### Original LiveArea template and layout RCOs, 2026-10-24

The next supplied files were decoded/read without running a compiler or changing
Moonlight's implementation:

- `template.xml`, SHA-256
  `0ab64825369e3721328399abd6b782713792b2bd0618b28e4fe3b00cecca1414`:
  `style="a1"`, content revision 3, and exactly `<title color="#94bd5cff"/>`
  between background and system-function-zone. Its Settings manual target is
  `sceman:settings`; frame3 contains the localized User's Guide link. This confirms
  the prior Moonlight title element's spelling/color/order against the supplied
  original; it does not explain the missing caption on the tested installation.
- `a1.rco`, SHA-256
  `a435a43d893bc6b18f3b54eb6355f9eba7c2b600651e7b7f2cf04f855cb3172e`:
  11 nodes, one template and four group/layout pairs. Frame1/2 are 260×260 at
  (-290,34)/(290,34), gate is at (0,32), frame3 is 840×150 at (0,-171).
  There are no text widgets, styles or textures, so this layout RCO does not
  define the caption.
- `a5.rco`, SHA-256
  `b34f4d2f0121a09c90a2039aa373bce287652de2717f6121b1eff9219956474c`:
  19 nodes, one template and eight group/layout pairs, with no text, styles or
  textures. Gate is at (240,66). Frames1–6 are 480×68 at x=-180 and
  y=128/60/-8/-76/-144/-212. Frame7 is 360×210 at (240,-141).
  This confirms the seven-slot geometry, without a title element.
- `music.rco`, SHA-256
  `55a0f2e41fa0098830f2542bdc3ba8ba9068783ddb0607514574e37547159d66`:
  40 nodes with gate (0,54), three text widgets at y=-84/-122/-158, four
  plane buttons and four textures. The text uses centred 20/28 px styles,
  with white inner text objects; no top-left title composition is present.

All three layouts share template ID hash `0x2e9374eb`. Their absence of a caption
does not exclude a shared shell template or dynamic creation. The next resource,
`vs0:vsh/shell/livearea_plugin.rco`, was subsequently supplied and decoded below.
At that resource-only stage, app/style eligibility and title-setting code were
unresolved. The shell trace below resolves the current profiles' admission gate;
the RCOs alone did not justify changing to a1 or claiming a system-only rule.

### Shared LiveArea title template, 2026-10-25

The supplied `livearea_plugin.rco` has SHA-256
`8f3256809c6e89182a03e5e4996ad564af462031b7ba6cb97eac8336034f142a`.
The complete decoded tree has 221 nodes: 19 templates, six text widgets, four
text styles and 19 textures. It contains a strong match for the top-left caption:

```text
template hash_399d0b3d                         tree 0x2f8
  group hash_d892138e                          tree 0x334
    size 840,500
    text hash_14f63523                         tree 0x38c
      style hash_3b29c32c
      align 1,0,0; pos -410,208,0; size 374,80,0

style_text hash_3b29c32c                       tree 0x1f2c
  textobj text_obj1
    font_size 28; bold 0; shadow 0
    align_x 0; align_y 0; text_align 0
    max_line_count 2; word_wrap 1; ellipsis 1
    color 1,1,1,1
```

The separate 840×500 parent, left inset and regular 28 px text agree with the
supplied LiveArea screenshot, unlike the centred Settings in-app header. This
is resource/geometry evidence, not an executed shell call trace. The widget has
no static label/string binding, and the style's default color is white rather
than the Settings template's green. Runtime code must supply content/color for
that caption path. The original ID names have not been recovered; `hash_*` names
above are descriptive labels for actual hashes, not guessed Sony identifiers.

The resource alone does not establish why Moonlight's `<title>` was invisible.
The subsequently supplied shell ELF resolves the admission check below. Loading
this template into the Moonlight PAF process would create an in-app widget; it
would not control the shell's LiveArea.

### Shell caption admission traced, 2026-10-25

The supplied `shell.self.elf` identifies itself as `SceShell`, SHA-256
`c98a5148326208f68b147a991a890fdf2de3d7b13e72f776ce1f840b3aa86089`.
It is ELF32 ARM EABI5 without section headers. LOAD0 maps file `0x100` to
VA `0x81000000`, file/memory size `0x541b74`; LOAD1 maps file `0x541c80` to
VA `0x81542000`, file size `0x6d38`, memory size `0x93fac`. Addresses below
are VAs in this image. BSS has no file-backed initial values and was not read
as if it did. The exact firmware version and pairing of supplied files remain
unverified.

**[code]** This is the caption path, now matched by actual hash references:

- Renderer `0x811a9796` dispatches parsed element type 5 to `0x811a74ce`
  at call site `0x811a99fa` after its update-mask check.
- `0x811a74ce` opens template `0x399d0b3d` via PAF `TemplateOpen`
  (`0x811a757a`), then finds group `0xd892138e` and text `0x14f63523`
  (`0x811a75d6` / `0x811a7642`). These match the supplied RCO.
- `0x811a766e` calls the text widget's virtual slot `0x11c`,
  `Widget::SetString(wstring const&)` in the installed PAF headers, with the
  controller's cached display name at `+20`. `0x811a768a` calls
  `Widget::SetColor` with the parsed element's four-float color at `+8`.
  The green color therefore need not be baked into the shared RCO style.
- Before any template/widget creation, `0x811a74e4` loads controller `+4`;
  `0x811a74ea` branches to the successful no-op return at `0x811a769c` if
  that word is nonzero. Thus a valid title element can be silently skipped.

The controlling word is a presentation kind derived from application metadata,
not the XML layout name or a PAF text-style flag:

1. Category classifier `0x81015370` selects shell application type 0 for
   `gda`, `gdb` and `wda`, except `NPXS10998` (type 2). The other-category
   table at file-backed VA `0x81542c00` contains `gd`, `gp`, `gdc`, `gdd`,
   `gpc`, `gpd`; matches select type 1 at `0x81015456`.
2. Descriptor filler `0x8129744e` calls `sceLsdbGetType` at `0x81297470`.
   Its native-launch case calls NID `0x9d27a87d` at `0x8129748a`, now named
   `sceLsdbGetShellApplicationType` in the
   [VitaSDK export map](https://github.com/vitasdk/vita-headers/blob/master/db/360/SceLsdb.yml).
   A zero result sets descriptor kind 0 (`0x8129749a`); every nonzero result
   sets kind 1 (`0x812974a2`). Launch types 2–5 select kinds 2/3/4/4.
   Only kind 0 copies the cached UTF-16 display name at `0x812974f6`.
3. The creation path fills this descriptor at `0x81298094`, then calls the
   LiveArea interface's first callback at `0x812980b2`. Registration at
   `0x8119a640`–`0x8119a648` assigns `0x8119accb` (Thumb).
   That wrapper calls owner constructor `0x8119b4cc`, which passes the
   descriptor to controller constructor `0x811a3baa` at `0x8119b540`.
   `0x811a3bc4` copies descriptor kind into controller `+4`, the exact word
   tested by the caption function.

Consequently **both current Moonlight profiles fail this native caption check**:
`CMakeLists.txt` selects `gd` for NORMAL and `gdc` for SYSTEM, and both select
shell type 1 / presentation kind 1 on this path. `MOONLIGHT_SYSTEM_APP=ON` and
UNSAFE do not imply the shell type 0 used by this caption. This statically
explains why the earlier correctly spelled `<title color="#94bd5cff"/>` can
produce no text. Changing a5 to a1, the title color, or the package display name
does not change that gate. The installed package/profile from the missing-title
screenshot was not inspected; this is binary/source evidence, not a captured
runtime trace of that installation.

Presentation kind 0 is necessary, not sufficient: the caption function also skips when the
owner identifier matches the string returned by ActivityDb NID `0xe6c23731`
(`0x811a74f4`–`0x811a7502`), or when its parent/group is unavailable. That
ActivityDb function's semantic name is unresolved. No universal rule for every
firmware or every category is claimed.

The maintainer subsequently requested removal of the texture-caption variant;
the original `bg0.png` is restored without a caption. A category change would
affect application launch/lifecycle classification and was not made.
No shell patch, title-ID/category change,
database access, promoter call, build, resource compilation or native execution
was performed. Input hash, file-backed category pointers, switch-table targets,
import NIDs and relevant instruction/call sites were checked read-only.

### Distinguishing gda, gdb and wda, 2026-10-25

These categories share the shell-type-0 classifier above, but other Shell paths
distinguish them. Do not infer identical launch, resource or memory behavior from
their shared caption classification.

The [VitaDevWiki PARAM.SFO field observations](https://www.psdevwiki.com/vita/PARAM.SFO#CATEGORY)
name `gda` as System Application, record Welcome Park (`NPXS10007`) as a `gdb`
example and User's Guide (`NPXS10060`) as a `wda` example. The table does not
give formal names for `gdb` or `wda`. Its `CONTENT_LOCATION` observations for
`wda` include `sceman:` / `sceman:near`. These examples are external research
observations, not SFO files supplied/verified in this investigation.

**[code]** The supplied Shell provides concrete differences:

- `gda` and `wda` share a special resource path. Predicate `0x8100e930`
  returns 0 for those two exact category strings and 1 otherwise. LiveArea
  construction at `0x8100ebe0`–`0x8100ec2a` and icon construction at
  `0x8100f718`–`0x8100f768` select their `BOOT_INSTALL_DIR` lookup. The lookup
  key `0xface5965` is independently reproduced by FNV-1a of that string,
  which is present in this ELF. This is resource-path evidence, not a claim
  that this category alone grants a particular process memory budget.
- `gdb` follows a different metadata/resource preparation path: predicate
  `0x8101023c` groups it with `gd`, `gp`, `gdc`, `gpc`. Metadata preparation
  `0x8103bf0a` excludes `gda`/`wda` with the first predicate, admits `gdb`
  with the analogous predicate `0x8103be66`, and uses the `ur0:appmeta`
  preparation path. This establishes a distinction from `gda`, without
  inventing an official expansion of the `gdb` name or a complete runtime
  contract from the Welcome Park example.
- `wda` additionally has a content-location branch that `gda`/`gdb` do not
  enter. At `0x8100fed0`–`0x8100ff00`, an exact `wda` match sets a descriptor
  word at `+36` to 2 (otherwise 0). At `0x8100fff0`–`0x8101007a`, it fetches
  key `0x39a02870` and copies the string to descriptor `+56`. That key is
  FNV-1a of the ELF's `CONTENT_LOCATION` string. Together with the observed
  `sceman:` values, this supports describing `wda` as a document/URI entry;
  no complete browser/URI dispatch trace or native execution was performed.

Practical distinction: `gda` is the system-application category; `gdb` is a
separate native-app category exemplified by Welcome Park and handled through
package-style metadata preparation; `wda` supplies a content/URI destination.
Exact Sony terminology for the latter two and a complete AppMgr budget,
suspend/coexistence and permission matrix remain unestablished. No Moonlight
category was changed, and no database, promoter, build or device operation ran.

### In-app Settings header composition

**[code]** `system_settings_main.rco` has this complete header composition:

```text
template hash_b047ffd3                         tree 0x23c
  plane hash_bebf0207                          tree 0x278
    style _common_style_plane_transparent
    align 0,2; size 960,64; pos 0,240
    box hash_d2290b7b                          tree 0x310
      horizontal layout; adjust 2,2; centred
      text main_page_title_text               tree 0x3d8
        style style_text_header
        size 760,0; align 0,4; adjust 0,2
    plane hash_966f95fd                        tree 0x480
      style hash_8d082ccd
      size 960,2; pos 0,0; anchor 0,1
  button hash_8211f03f                         sibling of header plane
    size 46,46; pos 32,208; anchor 1,0
```

`style_text_header` (tree `0x24bc`) explicitly binds its inner `textobj`:
32 px, bold, opaque white, centred X/Y, ellipsis enabled. The box can adjust to
content; the plain header text slot is 760 px wide. This is an ordinary PAF
plane/box/text composition supplied to the Settings UI, not evidence of a separate
PAF widget class called a system title bar. The sibling back-style button exists
in the template; its visibility on a particular page depends on runtime code.

The separator chain is **[code]**:

```text
plane hash_966f95fd
  -> style_plane hash_8d082ccd                 tree 0x2444
  -> planeobj.texture0 = hash_69cb3790
  -> texture hash_69cb3790                     tree 0x38c4
  -> compressed payload file 0x5530, length 0x322
```

The payload is a 960 x 2 indexed GIM, 3152 bytes after decompression. Its SHA-256 is
`de801d8a31d34014730390cf6250a39a05b9e1ba2a52e7dbf14222a52009f7e1`.
There is no `div_mode` or margin metadata on this texture. Row 0 is black, maximum
alpha 68/255 (26.7%); row 1 is white, maximum alpha 52/255 (20.4%). It fades toward
the sides; nonzero-alpha bounds are `(36,0)-(922,2)`.

This is **not** `_common_texture_ruled_line`. The supplied common texture is
328 x 4, with transparent outer rows, `div_mode="3x1"`, `div_ratio_h≈0.49`, and
maximum black/white alpha 90/18. The former project `header_line.png` was also
960 x 2, but had alpha maxima 51/46; decoded pixels are not identical to Settings.
The 150 x 4 Wi-Fi-local line (`hash_0cec900a`, margin 1/1, 912 x 2 template) is
another separator and must not be confused with this header asset.

**[code]** The ELF loads `vs0:app/NPXS10015/system_settings_main.rco` through
`paf::Plugin::LoadAsync` at `0x810001fa` (path assembled at `0x81000190`). Wi-Fi
page handling accesses the shared `main_page_title_text` at `0x8112081c` and calls
`Widget::FindChild` at `0x81120862`; this path replaces the title with the saved
AP name for `page_wifi_saved_ap_menu`. No direct reference to the header template's
numeric hash was identified in the ELF; the exact shared framework constructor
path was not fully reconstructed. The RCO dependency chain itself is explicit.

**[shot]** The screenshot has the system infobar above y≈32, a header band through
y≈96, and dark/light separator rows around y=95/96. Bright title pixels span
approximately x=370..588, y=49..82, including the descender and JPEG edges.

## Wi-Fi dot: connection state, with an animated intermediate state

**[code]** The Wi-Fi plugin owns two 30 x 30 textures used by this code path:

- `hash_fbd879ae` (texture node `0x5144`): bright green sphere/glow.
- `hash_9718c305` (texture node `0x51b0`): dim olive sphere with a bright upper half.

`hash_a6c087bd` is a translucent ring texture in the same file. Its presence does
not establish a third AP status: the traced Wi-Fi paths below switch the two sphere
textures. An ELF use of the ring at `0x81019dca` is in Bluetooth-plugin handling,
so a shared hash alone must not be assigned Wi-Fi semantics without plugin context.

The Wi-Fi template `hash_e454df4f` (tree `0x1808`) creates a `button`
`hash_c3232534` (tree `0x1834`), size 27 x 27, pos -302,0. Its style
`hash_1401d780` (tree `0x2a38`) binds the green texture as `glow_obj`.
The executable also creates a plain 27 x 27 PAF `Plane` dynamically. Runtime names
are `icon_blink_button` and `icon_blink_plane`; these names are ELF strings,
not invented names for the RCO IDs.

In the row-rendering routine beginning at `0x81124dfc`, the AP entry's word at
offset `0xb8` selects the presentation (`0x81125944`):

- States 2, 3 or 5 enter the animated branch (`0x81125948..0x81125952`). It uses
  the dim base texture (`GetTexture` at `0x81125d80`), opens the button template
  (`0x81125dfe`), obtains the green texture (`0x8112601a`) and calls
  `Widget::SetLoopEffect(7, true)` (`0x81126052`).
- State 4 enters the steady branch (`0x81126060`), uses the green texture
  (`GetTexture` at `0x81126480`) for the plain indicator, and removes the separate
  blink-button widget when present.
- Other states use the dim texture (`GetTexture` at `0x8112675e`) and remove the
  blink-button path when present.

A second indicator-rendering path contains the same state-4 test at `0x8112a3d6`,
green texture lookup at `0x8112a5d0`, dim lookup at `0x8112a650`, and animated
`SetLoopEffect(7,true)` at `0x8112a3d0`. Both paths pass the retrieved surface to
virtual slot `0x100`, matching `Widget::SetTexture(surface)` in the installed PAF
header. The exact timing/visual waveform of loop effect 7 was not measured; do not
invent a blink frequency from its numeric value.

The state is not taken from row focus. The status updater obtains it through
`0x8112d1fe -> 0x811401ac -> SceNetCtl NID 0xe8e8df18`, then writes that value to
the matching AP entry at offset `0xb8` (`0x81137d7a`). The connecting branch
(`0x81137bd8..0x81137be8`) tests 2/3/5 and selects message hash `0x500e7607`;
the connected branch selects `0xda7e42d0` (`0x81137cee..0x81137cfa`). Decoding
the English locale embedded in the Wi-Fi RCO gives respectively:

- `0x500e7607`: `Connecting... (%1)`.
- `0xda7e42d0`: `Connected. (%1)`.

The preceding branch bounds relevant active AP states to 2/3/4/5
(`0x811378f6..0x81137906`), so the connected alternative is state 4. This confirms
the interpretation: animated green during connection, steady green when connected,
dim otherwise. It does not mean that dim APs are unreachable. Individual names of
the intermediate states and the private NetCtl import remain unresolved.

**[shot]** Dot centres are approximately x=178, y=327/397/467/537, with 70 px row
pitch and title origin x≈208. This matches the 27 px slot and -302 position in a
960 px parent. The screenshot's OpenWrt is green and the summary says it is connected.

## Consequences for Moonlight

At the research baseline, Main/Apps had a comparable PAF plane/text/separator
composition, but used 26 px regular left-aligned text at x=80, without the centred
adjusting box. Search had an independent separator and a conditional empty-list
label at x=64, rather than a persistent title. Pairing and Stream lacked this
standard header. Resource reuse alone did not make those headers identical to Settings.

The previous replacement of the project's PNG with `_common_texture_ruled_line`
reuses a native PAF resource, but does **not** reproduce the exact Settings header
texture. The investigation itself did not change appearance.

**Requested implementation follow-up, 2026-10-23 [code]:** Main/Search/Apps now
share the Settings-style plane/horizontal-box/centred-text composition, with a
32 px bold title and a 760 px text slot. The maintainer explicitly chose
`_common_texture_ruled_line` for the separator; its plane retains 960 x 4 geometry.
Search's permanent localized title is separate from its conditional empty-list
label. Pairing/Stream retain their existing layouts and corner-button navigation
is unchanged. See UI.md section 5.1 for current details and pending Vita validation.

The sphere artwork can be reused for a PC availability indicator, but availability
is a separate product meaning. Saved-host `fill_host()` currently sets `online=0`;
mDNS discovery sets `online=1` on arrival, without expiring results during that
scan. Wiring those fields directly would make all saved PCs dim regardless of
actual reachability. A real availability feature needs backend/service-owned
observations and main-thread UI delivery, preserving the existing row/checkbox
interaction. Do not derive availability from pairing or run network calls in the
row factory. Artwork extraction, state-branch inspection and XML checks do not
validate such a feature; no PC indicator has been implemented by this research.

## Applying the indicator to PC rows: implementation assessment

**Source investigation, 2026-10-23.** The proposal below was followed by the
[trial implementation](#trial-implementation); hardware validation remains open. The useful meaning
for the PC browser is recent reachability of the configured GameStream endpoint.
It should not inherit Wi-Fi's connected/connecting meaning without an explicit
product decision. Neither a stored `paired` flag nor `ConnectionService::State()`
provides live availability for every row.

### Existing mechanisms and their limits

- `legacy_device_store.cpp::fill_host()` assigns `online=0` without a request.
  `legacy_host_discovery.c::on_mdns_host()` assigns `online=1` on discovery; duplicate
  entries return early. Its worker lasts 100 x 100 ms, not continuously, and the
  published host array does not expire entries. The sniffer's `last_seen` is used
  for table-slot replacement, not a per-PC reachability lifetime. Missing mDNS
  does not establish that a saved/manual/remote PC is offline.
- `ConnectionService::Connect()` reserves foreground ownership, opens native busy,
  cancels abandoned pairing and queues `ConnectJob`. `moonlight_api_connect_host()`
  replaces the current server, invalidates Apps and may persist host identity.
  Main/Search open Apps or Pairing after success. Reusing Connect as a probe would
  change application state; showing its row pulse would usually duplicate the
  existing busy dialog before the list is covered by the next page.
- `legacy_gamestream_init()` is not a stateless probe even with a temporary server
  object: it loads/creates global client identity/credentials and initializes curl.
  `legacy_gamestream_shutdown()` frees global `s_cert`/`s_private_key`, clears
  `s_unique_id`, and calls `curl_global_cleanup()` (lines 2079..2106 at this review).
  Its HTTP path also shares a mutex and global last-error state. A probe must not
  borrow that init/shutdown pair or the active server's curl handle.
- Existing `load_server_info()` already implements `/serverinfo` parsing and pin
  verification through its transport, but is static, mutates a server snapshot,
  and requests a 15-second timeout. `http_request()` sets a 10-second connect
  timeout. These are foreground connection settings, not proposed probe settings.
  `legacy_gamestream_refresh_server_info()` requires the current paired server.
- The installed VitaSDK already exposes socket connect, resolver and epoll APIs;
  no new networking dependency is necessary for a bounded TCP-port check. Their
  use for this feature is not compiled or hardware-tested by this investigation.

### Recommended minimum

Start with two artwork states and a short, cancellable TCP connection attempt to
the same `host.internal`/`host.port` route used by the current Connect path. Resolve
hostnames outside the PAF thread. A successful handshake means **the configured
port answers**, not authenticated Sunshine, successful pairing, an idle host app,
or guaranteed streaming. A different service on that port can give a false positive.
If the product requires confirmed Sunshine identity rather than port reachability,
this minimum is insufficient: use the `/serverinfo` option below from the start.

Green means a recent positive observation. Dim means no fresh confirmation,
including unchecked, expired, failed and locally cancelled checks; do not claim
that every dim PC is powered off. Keep the last protocol/transport outcome distinct
internally from a local execution failure. Expire positive observations, keep them
only in memory and never persist availability in `device.ini` or AppSettings.

One backend-owned scan, exposed through existing HostService/backend boundaries,
can publish a complete observation snapshot. Check on entry/return to the PC list;
stop scheduling and cancel/reap outstanding work before admitting a conflicting
foreground action, leaving the page, opening Settings or entering streaming.
Deliver cleanup completion asynchronously; do not block PAF by joining a network
worker on its main thread. Bound DNS/connect time and the scan's resource use. A future periodic refresh must
run only while the list is active and must not enqueue overlapping scans. This
initial entry/return refresh is a snapshot feature, not continuous monitoring.

Results need stable identity and a scan generation: list indices, row tokens and
discovery IDs are not persistent PC identity. Reject results for deleted/replaced
hosts or obsolete scans. Use UUID/address+port matching consistent with the existing
host-identity rules, without changing persistence formats or reassigning identities.
Queue notifications through MoonlightApp; worker callbacks never touch PAF.
`HOSTS_CHANGED` is coalesced as a snapshot invalidation, so the backend must retain
all observations: its event `host_id` cannot carry the only copy of a per-PC delta.

### UI integration

Reuse the extracted green/dim PNG artwork (originally 30 x 30) in a 27 x 27
noninteractive `plane` in both `template_host_list_item` and its selection variant.
Keep the PC icon and checkbox. A proposed layout puts the normal dot at row
x=178 and the title/address at x=208; selection adds the existing 80 px offset
(dot x=258, text x=288). Text widths 667/587 retain the current right edge x=875.
These are source-layout proposals, not measured Moonlight screenshots or Vita checks.

Factories initialize the dot from the latest observation; main-thread updates
change only existing generated cells (`ListView::GetListItem` is declared by the
installed PAF SDK). Missing/not-yet-generated cells simply use the snapshot later.
Do not keep stale widget pointers or rebuild the full list for every result:
current `RefreshHosts()` deletes/reinserts cells and regenerates row tokens.
Keep keyboard focus, scrolling and multi-selection stable. Source checks and a
Vita run must confirm generated-cell lookup and texture switching behavior.

Omit the connecting pulse in the first version: it adds little behind the existing
modal busy dialog. If explicitly requested later, use native PAF loop effect 7 for
the selected connection attempt and remove it on every terminal/cancellation path;
do not invent a second animation timer or replace native foreground progress.

### When `/serverinfo` is required

A read-only probe should reuse existing parsing, URL/port and pinned-certificate
rules while keeping per-request handles/results isolated from the active session.
It must not initialize/persist a PC, generate credentials, pair, select an app or
clear global curl/crypto state. Global client/transport ownership must first be
made safe for this use; copying today's init/shutdown path is not that separation.
Never turn a TLS-pin failure into success with a plaintext fallback. Unpaired
discovery can establish service presence without establishing trust, and pairing
remains a separate action. HTTP reachability does not mean that `currentgame` is
zero; a busy Sunshine host can still answer and the existing remote-Quit flow
owns launch conflicts. Keep network/state changes separate from the artwork change.


### Trial implementation

Implemented on 2026-10-23: the minimum TCP reachability variant, two static Wi-Fi
spheres in Main/Search and selection rows, no connecting pulse. Current geometry,
refresh/expiry policy and ownership are canonical in [UI.md §5.2](UI.md).
HostService owns a dedicated one-worker PAF queue, and the adapter exposes a
stateless native socket probe. Immutable per-job host snapshots isolate obsolete
results. UUID plus exact address/port binds observations to rows; names and row
indices do not carry identity. Cancelling a scan invalidates all of its positives.
The active job is checked on the main thread; observations and expiration become
a coalesced MoonlightApp event, not worker-to-widget calls.

The trial requests native resolver timeout/retry 1/1 and checks cancellation when
that call returns. TCP waits have a one-second process-clock deadline, checking
cancellation every 10 ms. DNS timing and resolver cancellation latency are native
acceptance items, not a claim established by Python mocks. No libcurl or GameStream
session state is involved. Enqueue failure remains dim and preserves the previous
successful job as Connect's cleanup barrier. Teardown waits for the queue before
network termination. Background network activity runs only for a requested active
list scan. Follow-up after the maintainer observed Main's dot dimming over time:
active Main/Search now repeat unchanged scans at a 15-second start-to-start
interval, waiting for the previous scan to finish. Pending replacements preserve
fresh previous positives with their original 30-second expiry, avoiding a dark
flash on every refresh. A failed check still turns dim immediately. Hidden lists
and conflicting workflows cancel scheduling as before; long serial scans may
still exhaust freshness. Periodic refresh needs maintainer build/Vita validation.

Non-build checks interpret the actual probe/predicates with mocked Vita results:
TCP immediate/pending success, refused/wrong/error readiness, SO_ERROR failures,
creation/setup/poll failures and acquired-handle cleanup, timeout/cancellation,
DNS success/failure/cancellation, identity replacement and the exact TTL boundary.
Submission failure preserves the drain barrier; source wiring checks cancellation
at foreground admission and waiting inside Connect's worker. Event checks cover
coalescing and main-thread dispatch. These do not run native threads/networking.

Maintainer acceptance: build CXML/application; compare Main/Search/selection dots
with the official screenshot; scroll enough rows to force cell reuse; confirm
selection/focus survive result changes; test answering/refused/silent ports,
hostnames and DNS failure, active-list refresh across several minutes, disappearance
when a PC stops answering, 30-second expiry and list return refresh; select a PC
while a check is pending; leave/reopen Search, IME and Settings; stream/stop/return;
exit during a pending check. A positive from an unrelated TCP service is an
intentional limitation of this trial, not proof of authenticated Sunshine.
