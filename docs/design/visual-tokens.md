# Visual tokens

Status: **frozen** for the A/B presentation-layer prototypes.

These are the shared inputs to both prototypes. Both must consume these exact
values so that the comparison is about the technology, not about who picked the
nicer colours. Do not tune them inside a prototype: if a value is wrong, change
it here and both prototypes change together.

The direction these values serve is recorded in [desktop-ux.md](desktop-ux.md)
and [ADR 0007](../adr/0007-branded-dark-visual-system.md).

## Surfaces

Three surfaces and one hairline. No gradients, no shadows, no elevated cards.
The video stage is the darkest thing in the window so the frame is the brightest.

| Token | Value | Use |
| --- | --- | --- |
| `stage` | `#0B0C0D` | Video ground, timeline track ground |
| `app` | `#131518` | Toolbar, transport, window ground |
| `panel` | `#1A1D21` | Sidebar, Clip editor |
| `rule` | `#2A2E34` | 1px hairlines between panes and rows |
| `control` | `#22262B` | Buttons, fields, segmented controls |
| `control-hover` | `#2C3138` | Hover |
| `control-border` | `#343941` | 1px control border |
| `control-disabled` | `#1B1E22` | Disabled control ground |

## Text

| Token | Value | Use |
| --- | --- | --- |
| `text` | `#E8EAED` | Primary |
| `text-muted` | `#8A9099` | Section labels, secondary metadata |
| `text-faint` | `#5E646C` | Ruler labels, disabled, placeholders |

## Accent

One saturated signature hue, drawn from the Catapult reference family and
deliberately outside the Category palette so the two can never be confused.

| Token | Value | Use |
| --- | --- | --- |
| `accent` | `#E4306B` | Playhead, primary action, selection |
| `accent-hover` | `#F0538A` | Hover on accent |
| `accent-pressed` | `#C41F58` | Pressed |
| `accent-on` | `#FFFFFF` | Text on accent |
| `selection` | `#33172A` | Selected row ground |

The accent is reserved for exactly three things: the playhead, the primary
action, and selection. Nothing else in the interface is allowed to use it.

## Category palette

Fixed. Ten colours at roughly constant lightness and chroma. Users choose from
this palette; there is no free colour picker. The magenta/pink band is left
empty so no Category can collide with the accent.

| # | Name | Value |
| --- | --- | --- |
| 1 | Rot | `#E2564A` |
| 2 | Orange | `#DE8241` |
| 3 | Bernstein | `#C9A227` |
| 4 | Limette | `#8FAE3C` |
| 5 | Gruen | `#4BA46A` |
| 6 | Petrol | `#3AA6A0` |
| 7 | Cyan | `#3E9BC4` |
| 8 | Blau | `#5B87D6` |
| 9 | Violett | `#8B7BD8` |
| 10 | Purpur | `#A96BC0` |

Timeline range fills use the Category colour at 40% alpha over `stage`, with a
1px top edge at full colour. Clip rows use a 3px full-colour bar at the row's
leading edge. Category colour is always secondary to the Category name.

## Typography

Bundled, so both platforms render identically. Two weights only: Regular (400)
and Medium (500).

- UI family: **Inter** (SIL OFL), bundled in `assets/fonts/`.
- Timecode family: **JetBrains Mono** (SIL OFL), tabular figures.

| Role | Size / weight | Family |
| --- | --- | --- |
| Document title | 15 / 500 | Inter |
| Row title (Clip name) | 13 / 500 | Inter |
| Body, controls, form fields | 12 / 400 | Inter |
| Section label | 11 / 500 | Inter |
| Timecode | 12 / 500 | JetBrains Mono |
| Ruler label | 10 / 400 | JetBrains Mono |

No letterspacing. The previous system letterspaced 9px and 10px capitals, which
is below the size at which letterspacing reads as anything but noise.

## Spacing, metrics, shape

4px base unit. Pane gutters 16px, control gaps 8px.

| Metric | Value |
| --- | --- |
| Toolbar height | 44 |
| Transport height | 56 |
| Timeline total height | 60 (16 ruler + 44 track) |
| Clip row height | 32 |
| Sidebar width | 300 default, 260 min, 420 max, collapsible |
| Clip editor width | 360 |
| Control height | 28 |
| Corner radius | 3 on controls, 0 on panes |
| Border width | 1 |

Minimum designed window size is **1440x900**.

## Icons

One family: **Lucide** (ISC licence), as SVG, recoloured by state, crisp on
HiDPI. Stroke weight 1.75. 20px in the transport, 16px everywhere else.

The existing raster SF Symbols exports in `icons/` are retired. They sit on
inconsistent grids (27x26, 47x25, 32x32), cannot be recoloured for state, do not
scale for HiDPI, and dress a cross-platform application in one platform's
iconography.

## Canonical prototype fixture

Both prototypes render the same Analysis so the screenshots are comparable:

- Two Source videos: `halbzeit-1.mp4` (45:00, active) and `halbzeit-2.mp4` (42:30).
- Twelve Clips across five Categories, durations between 6s and 22s, spread
  across both Source videos, including two Clips less than 12 seconds apart so
  the minimum-range-width behaviour is visible.
- Categories drawn from palette entries 1, 5, 7, 8, 2.
- Analysis title `SG Beispiel - TV Muster`, playhead at 00:14:03, the Clip
  `Tor von rechts aussen` selected.
