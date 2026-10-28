# Photos: folded parent screen and Main → Apps

Read-only investigation, 2026-10-28. Moonlight baseline: `9a22dc6` on `master`.
The request is to identify Photos' visible parent screen and explain how to use
that navigation for Moonlight's PC → applications path. No runtime UI changes,
builds, resource compilation or hardware execution were performed.

**Follow-up, 2026-10-28:** Main ↔ Apps now source-implements the prototype in
[UI guide §5.6](UI.md#56-photos-folded-parent-navigation--2026-10-28). The original
research/baseline plan below is retained as evidence. Five new serial source
checks and the existing resource/LiveArea checks pass; build and Vita rendering
remain pending. No firmware binary is copied into the application.

## Finding

**[code]** Photos implements a local stack of retained content widgets, with
position, quaternion and alpha animation through native PAF. Its own embedded
name `furl_stack_overlay_button` identifies the folded-screen interaction.
The stack implementation is code inside Photos, not a newly discovered exported
Sony page-navigation service. The previous widget remains transformed while a
child is current; popping the child restores the saved parent state.

**[shot]** In the supplied 960 × 544 screenshot, the previous category list is
visible at the left, behind the All grid. The grid starts at x=115 and ends
before x=846. These are reference-image bounds, not a prescribed Moonlight list
width. A still image alone does not establish animation duration or gesture
behavior; the static code supplies the stack/animation evidence below.

This is more than changing `Plugin::TransitionType_SlideFromBottom` to
`SlideFromRight`. Photos' retained parent has a separate position, Y rotation
and alpha. Although the installed PAF exposes `Type_3D_SlideToBack1` and
`Type_3D_SlideToBack2`, their names do not establish equivalence to Photos.
The inspected Photos stack calls the lower-level widget animation APIs.

## Inputs and reproducibility

The supplied firmware version is unknown. Addresses below are virtual addresses
in this exact ELF, not reusable firmware API entry points.

- `eboot.bin.elf`, `/home/nowaru/Downloads/NPXS10004/eboot.bin.elf`:
  SHA-256 `54118fb18fb28c8627ad41145aa6ea35724c0538fc4103bb5c7833a543f4f1fb`.
- `photocam_plugin.rco`, `/home/nowaru/Desktop/photocam_plugin.rco`:
  SHA-256 `b754d14074a0244b0c51fc550cf8e78205647c44b89d2914d3d9787ceff9e3c5`.
- `template.xml`, `/home/nowaru/Downloads/sce_sys/livearea/contents/template.xml`:
  SHA-256 `f6b513d2cfa66b99e7f323751b2ab6a09d1e23ee398dfcafe93713d7424caa19`.
  Root is `livearea`, style `a3`, with camera/gallery launch targets. This controls
  the shell's LiveArea, not the in-app navigation in the screenshot.
- Screenshot: `codex-clipboard-78d02f45-8e34-4b8b-8ab2-3e2a2cd69652.png`.

Method: decode ELF program/module/import headers with Python's `struct`, match
NIDs to the installed `vitasdk-paf-component/build/build_libpaf/ScePaf.yml`,
demangle names, then disassemble the extracted first LOAD with installed
`arm-vita-eabi-objdump -D -b binary -m arm -M force-thumb --adjust-vma=0x81000000`.
The first LOAD maps file offset `0xe0` to VA `0x81000000`; module info is at
file `0x101354` and identifies `ScePhotoCam`. The import range is
`0x811012f0..0x81101de8` (1175 function imports). The RCO tree and attributes
were decoded read-only using its CXML header/tables. Temporary data and
annotation/check scripts are in `/tmp/photos-transition-research/`.

## Recovered stack behavior [code]

- Photos constructs its navigation stack at object offset `0x1cc` in
  `0x81005c96..0x81005c9c`, calling local constructor `0x8109e2a0`.
- Content creation at `0x810080a0` calls PAF `Plugin::CreateWidget`; the new
  widget is registered with that stack at `0x8100812c..0x81008132`, calling
  `0x8109ddc2`. Further push sites are `0x81008480` and `0x8100873c`.
- `0x8109da40` snapshots widget position, quaternion, meta-alpha and alignment.
  It adjusts the horizontal pivot using half the view width and preserves the
  visible position with `SetPosCenter`. Consequently raw target X values below
  must not be copied onto an ordinary center-pivot Moonlight scene unchanged.
- `0x8109e3b0` updates retained stack layers: current returns to its captured
  transform; the immediate parent uses offsets at `+36..+48`; older ancestors
  use `+52..+64`. Its vtable entry at `0x811500e8` contains Thumb pointer
  `0x8109e3b1`. Both push and pop invoke this update through vtable slot `+12`.
- At `0x8109e554..0x8109e5a6` the immediate parent target is constructed from
  the saved position, a half-view-width pivot compensation, configured X/Z
  targets and Y rotation (`quaternion::FromEulerAnglesYXZ`).
- Local helper `0x8109dbfe` cancels the prior position/quaternion/meta-alpha
  animations and calls `Widget::SetPos` (`0x8109dcac`), `SetQuat`
  (`0x8109dd2a`) and `SetMetaAlpha` (`0x8109ddb6`). Position/quaternion timers
  use function 23, `Timer::FUNC_CIRQ_OUT` in the installed header. Alpha uses
  linear easing over 0.8 times the configured duration.
- `0x8109e138` removes the top entry and invokes the layer update;
  `0x8100743a` is a caller. The restored current layer uses the recorded
  position/quaternion/alpha at `0x8109e6e0..0x8109e6f6`. This supports a
  persistent folded parent plus animated return, not just an entrance effect.
- The overlay name is referenced at `0x8109e7cc..0x8109e7d6`. The parent path
  also creates a transparent button (`0x8109e5ea..0x8109e6bc`) and attaches an
  event listener. Exact touch/back interaction was not tested on hardware.

Native imports used by the animation helper:

- NID `0xE29AB31F`: `Widget::SetPos`, stub `0x810fffc4`.
- NID `0xF8D257AF`: `Widget::SetQuat`, stub `0x81100164`.
- NID `0x543F0959`: `Widget::SetMetaAlpha`, stub `0x810ff494`.

The installed YAML and import tables are authoritative for NID matching;
firmware stubs/addresses are evidence only, never calls to add to Moonlight.

## Constructor defaults [code, not hardware measurements]

`0x8109e2a0..0x8109e340` initializes three sets of X/Z/Y-angle/alpha values:

- Incoming content (`+20..+32`): X `960`, Z `330`, Y rotation `−π/2`, alpha `0`.
- Immediate parent (`+36..+48`): X `−116`, Z `−150`, Y rotation `+π/2`,
  alpha `0.15`.
- Older ancestors (`+52..+64`): X `−116`, Z `−150`, Y rotation approximately
  `1.8535396 rad` (`106.2°`), alpha `0`.
- Duration (`+76`): `500 ms`; therefore the helper's alpha timer is `400 ms`.

These are recovered defaults of Photos' own stack. Incoming targets are applied
before interpolation to the saved foreground state. Parent X is assembled with
`−view_width/2` after the pivot adjustment. They are not independent screen-pixel
coordinates or proof that every Photos path retains these defaults.

## Moonlight integration plan

**[code] Behavior at research baseline:** `Apps::Apps()` requests `SlideFromBottom` for open
and close. `Base` retains Main and only deactivates it. Main and Apps each draw
an opaque full-screen `_bg_texture`; Apps uses the 960-wide generic list. Thus
retention already exists, but an opaque Apps background covers Main. Changing
just the transition enum cannot expose the folded host list.

**Original proposal (follow-up implementation described in UI guide §5.6):**

1. Keep the existing `page::Base` stack. Add CXML content containers for the
   parts of Main/Apps that move, with the background outside those containers.
   Make Apps' relevant background transparent or share the stable backdrop.
   Leave title/back/bottom controls outside the moving list where appropriate.
   Give the foreground content a deliberate left gutter so it cannot cover the
   folded parent; derive its final bounds from Moonlight/Vita screenshots.
2. Animate those containers with native `Widget::SetPos`, `SetRot` (one Y axis
   gives the required equivalent rotation), `SetMetaAlpha` and `paf::Timer`.
   Use the recovered 500 ms/circular-out behavior as the first prototype and
   account explicitly for the pivot; do not substitute raw scene coordinates.
   Avoid manually updating transforms each frame or capturing Main as an image.
3. Tie the folded-Main state to a successfully created Apps page. Restore Main
   when Apps closes; restore original transforms, opacity and focus. Keep the
   deactivated parent from accepting actions while Apps is current. Input
   admission during the animation must be released by completion callbacks,
   with no main-thread sleeps or guessed timeout for resource cleanup.
4. Cover both entry routes: a paired Main connection creates Apps directly;
   successful PIN pairing creates Apps then deletes the non-current Pairing
   page. Resolve Main by identity, not merely `GetCurrent()` at Apps creation,
   and do not replay/undo the effect when Pairing is removed from mid-stack.
   Invalid Apps creation must leave Main unchanged. Preserve progress/error
   dialog ownership and restore behavior for Apps refresh failure/cancellation.
5. Apply this only to browsing Main ↔ Apps. Stream remains the existing
   full-screen page with its own graphics priority, power and lifecycle rules.
   OptionMenu, Settings and PIN retain their current presentation. Discovery
   must stay paused whenever Main is the visible but inactive ancestor.

**[open]** The PAF APIs are available in the installed headers/stubs, but their
projection, clipping, scene layering, exact strip width and rapid Back/enter
behavior in Moonlight require the maintainer's build and Vita run. Required
acceptance includes direct paired entry, PIN → Apps → Main, refresh failure,
empty apps, repeated entry/back, focus/scroll retention and Stream → Apps → Main.

Verification performed: three input SHA-256 checks; LiveArea XML root; all 1175
function imports; the three animation import NIDs/call sites; the stack update
vtable entry; 11 constructor constant fields; the embedded furl-stack name;
RCO tree boundaries (769 nodes); and `git diff --check`. These are static
checks, not compilation, rendering or device acceptance.
