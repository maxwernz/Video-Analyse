# Own a branded dark visual system instead of a native-first appearance

Video Analyse presents itself through its own dark visual system: bundled
typography, one open icon family, three surfaces separated by hairlines, one
saturated signature accent, and a fixed Category palette. It does not aim to look
like a default macOS or Windows application. Platform *behaviour* is kept where it
is behaviour rather than appearance: the native menu bar, native window controls,
native file dialogs, and platform shortcuts all stay.

The trigger was direct evidence. The shipped interface was captured at 1440x900 in
[docs/design/current-ui](../design/current-ui) and judged not merely plain but
cheap. The failures are specific and none of them are failures of restraint: a
product wordmark strip duplicating the native title bar, raster icons from three
different optical grids next to a stock `QComboBox`, ten near-identical greys
inside twenty luminance points so panes never separate, proportional digits so
timecode columns do not align, a 30px timeline with no ruler and 3px invisible
Clip ranges, and clipped duration fields in the Clip editor. The reference
applications the owner accepts as professional -- Catapult, In-Play, TactiCode,
captured in [docs/design/references](../design/references) -- are all branded and
none of them look native.

## Considered options

- **Native-first Qt Widgets appearance.** Cheapest, most accessible, best platform
  citizenship, and it inherits platform theme changes for free. Rejected as an
  *appearance* strategy because it cannot reach the accepted references: they are
  branded interfaces, and a native-first application asymptotically approaches
  "default", which is the exact impression being escaped.
- **A branded, self-contained dark visual system.** Chosen. Owns the surfaces the
  user looks at constantly -- timeline, Clip list, transport, toolbar, forms --
  and accepts that every deviation from platform convention becomes a permanent
  maintenance obligation.
- **Follow the OS light/dark theme.** Deferred. Two themes double the design and
  test surface and are the most common way a Qt application ends up looking
  half-finished. Video Analyse ships one dark theme, tuned properly.

## Consequences

- The presentation layer is now a real, owned artefact. The token values are frozen
  in [visual-tokens.md](../design/visual-tokens.md); no surface may invent its own.
- The `VIDEO ANALYSE` wordmark strip is deleted and replaced by a working toolbar.
  A single-window desktop tool does not announce its own name in its chrome.
- `icons/*.png` and `icons/old icons/` are retired in favour of one SVG family.
- Category colour becomes a fixed ten-entry palette rather than a free colour
  choice, so no Analysis can be tuned into something ugly and none can collide
  with the accent.
- The interface is no longer theme-adaptive. High-contrast and light-mode users are
  not served by this release, which is accepted for internal distribution.
- Choosing branded over native is what makes the QML presentation layer a serious
  candidate rather than an obvious loss. It is still only a candidate: the choice
  between Qt Widgets and Qt Quick is deliberately *not* decided here and is settled
  by the prototypes described in [desktop-ux.md](../design/desktop-ux.md).
