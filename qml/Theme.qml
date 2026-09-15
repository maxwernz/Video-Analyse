pragma Singleton
import QtQuick

/*
  The frozen tokens from docs/design/visual-tokens.md, transcribed once.

  Nothing else in this application is allowed to write a colour or a metric.
  If a value here is wrong it is wrong in the token spec first; change it
  there, then here, and never in a component. `tests/test_qml_workspace.py`
  holds the line by failing on a colour literal or a bare metric found in any
  other QML file.
*/
QtObject {
    id: theme

    // Surfaces -- three surfaces and one hairline.
    readonly property color stage: "#0B0C0D"
    readonly property color app: "#131518"
    readonly property color panel: "#1A1D21"
    readonly property color rule: "#2A2E34"
    readonly property color control: "#22262B"
    readonly property color controlHover: "#2C3138"
    readonly property color controlBorder: "#343941"
    readonly property color controlDisabled: "#1B1E22"

    // A hover that must stay quieter than `controlHover`, for a segment
    // inside a control that is already drawn on `control`.
    readonly property color controlSubtleHover: Qt.rgba(1, 1, 1, 0.03)

    // Text
    readonly property color text: "#E8EAED"
    readonly property color textMuted: "#8A9099"
    readonly property color textFaint: "#5E646C"

    // Accent -- the playhead, the primary action and selection. Nothing else.
    readonly property color accent: "#E4306B"
    readonly property color accentHover: "#F0538A"
    readonly property color accentPressed: "#C41F58"
    readonly property color accentOn: "#FFFFFF"
    readonly property color selection: "#33172A"

    // The fixed Category palette. Ten colours at roughly constant lightness
    // and chroma, with the magenta/pink band left empty so no Category can
    // collide with the accent. There is no free colour picker.
    readonly property var categoryPalette: [
        "#E2564A",  // 1  Rot
        "#DE8241",  // 2  Orange
        "#C9A227",  // 3  Bernstein
        "#8FAE3C",  // 4  Limette
        "#4BA46A",  // 5  Gruen
        "#3AA6A0",  // 6  Petrol
        "#3E9BC4",  // 7  Cyan
        "#5B87D6",  // 8  Blau
        "#8B7BD8",  // 9  Violett
        "#A96BC0"   // 10 Purpur
    ]

    // Typography -- bundled, so both platforms render identically.
    readonly property string uiFamily: "Inter"
    readonly property string monoFamily: "JetBrains Mono"
    readonly property int regular: Font.Normal   // 400
    readonly property int medium: Font.Medium    // 500

    readonly property int sizeTitle: 15
    readonly property int sizeRow: 13
    readonly property int sizeBody: 12
    readonly property int sizeLabel: 11
    readonly property int sizeTimecode: 12
    readonly property int sizeRuler: 10

    // Spacing, metrics, shape -- 4px base unit.
    readonly property int unit: 4
    readonly property int gutter: 16
    readonly property int gap: 8

    readonly property int toolbarHeight: 44
    readonly property int transportHeight: 56
    readonly property int rulerHeight: 16
    readonly property int trackHeight: 44
    readonly property int timelineHeight: rulerHeight + trackHeight
    readonly property int clipRowHeight: 32
    readonly property int categoryHeaderHeight: 30
    readonly property int sidebarWidth: 300
    readonly property int sidebarMinimum: 260
    readonly property int sidebarMaximum: 420
    readonly property int editorWidth: 360
    readonly property int controlHeight: 28
    readonly property int radius: 3
    readonly property int border: 1

    // ADR 0006 says "about three pixels"; it is a hit target as well as a
    // drawing, which is why it is a token rather than a painting detail.
    readonly property int minimumRangeWidth: 3

    // Metrics the token spec does not name.
    //
    // The shell needs a handful of numbers the spec never froze. They live
    // here rather than in the component that wants them, so that "no component
    // defines a metric of its own" stays literally true and so that the next
    // surface finds them instead of inventing a second value.
    readonly property int toolbarSeparatorHeight: 18
    readonly property int toolbarActionSpacing: 2
    readonly property int dirtyMarkerSize: 6
    readonly property int tooltipHeight: 22
    readonly property int tooltipOffset: 6
    readonly property int tooltipDelayMs: 550
    readonly property int splitterWidth: 5
    readonly property int paneAnimationMs: 130

    // The transport. The token spec freezes the row's 56px and says the play
    // control is "rendered larger than its neighbours"; these are the sizes
    // that were drawn against that, and the play control is the only round
    // one in the window.
    readonly property int transportButtonSize: 34
    readonly property int transportPlaySize: 46
    readonly property int transportPlayInset: 3
    readonly property int transportClusterSpacing: 2
    readonly property int transportGroupSpacing: 12
    readonly property int timecodeSpacing: 6
    readonly property int seekLabelSize: 9
    readonly property int seekLabelOffset: 1
    readonly property int playIconOffset: 1
    readonly property int controlPadding: 12
    readonly property int rateSegmentWidth: 38
    readonly property int segmentIndicatorHeight: 2
    readonly property int segmentIndicatorInset: 12
    readonly property int volumeSliderWidth: 72
    readonly property int volumeTrackHeight: 3
    readonly property int volumeKnobSize: 10

    // The timeline. The token spec freezes the 60px anatomy, the 40% range
    // fill and the 2px accent playhead; the rest of these are the sizes the
    // reference timeline was drawn against.
    readonly property real rangeFillAlpha: 0.40
    readonly property real rangeSelectedAlpha: 0.62
    readonly property real rangeOutlineLighten: 1.5
    readonly property int majorTickHeight: 6
    readonly property int minorTickHeight: 3
    readonly property int rulerLabelGap: 3
    readonly property int rulerLabelTurnPx: 12
    readonly property int playheadWidth: 2
    readonly property int playheadHandleWidth: 10
    readonly property int playheadHandleRadius: 2
    readonly property int playheadGrabPx: 9

    // Stacking inside the timeline: the ranges are the ground, the playhead
    // draws over them, the tooltip over that, and the one mouse area over
    // everything, because the whole surface scrubs.
    readonly property int playheadLayer: 30
    readonly property int tooltipLayer: 40
    readonly property int interactionLayer: 50

    // A Clip range: the Category colour at 40% alpha over the stage, at 62%
    // when it is the selected Clip, outlined in a lighter version of itself.
    // These are the only two colours in the application derived from a value
    // the interface is given rather than from a token, which is why the
    // derivation lives here with the tokens.
    function rangeFill(tint, selected) {
        return Qt.rgba(tint.r, tint.g, tint.b,
                       selected ? rangeSelectedAlpha : rangeFillAlpha)
    }

    function rangeOutline(tint) {
        return Qt.lighter(tint, rangeOutlineLighten)
    }

    // Icons -- 20px in the transport, 16px everywhere else. The stroke weight
    // is applied by `icon_family.py` on the way to the renderer.
    readonly property int iconSize: 16
    readonly property int transportIconSize: 20

    // The window itself. The designed size is 1440x900; the smaller minimum is
    // what the shell was actually laid out against.
    readonly property int windowWidth: 1440
    readonly property int windowHeight: 900
    readonly property int windowMinimumWidth: 1200
    readonly property int windowMinimumHeight: 760

    // One SVG per icon, recoloured on the way to the renderer by the `icon`
    // image provider, because Qt's SVG renderer honours neither `currentColor`
    // nor a stroke override.
    function icon(name, color) {
        return "image://icon/" + name + "?color=" + encodeURIComponent(color)
    }
}
