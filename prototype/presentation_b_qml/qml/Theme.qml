pragma Singleton
import QtQuick

/*
  The frozen tokens from docs/design/visual-tokens.md, transcribed once.

  Nothing else in this prototype is allowed to write a colour or a metric.
  The values are consumed exactly as the spec froze them; where the spec and
  the prototype disagreed, the disagreement is recorded in FINDINGS.md rather
  than tuned away here.
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

    // Typography
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
    readonly property int sidebarWidth: 300
    readonly property int sidebarMinimum: 260
    readonly property int sidebarMaximum: 420
    readonly property int editorWidth: 360
    readonly property int controlHeight: 28
    readonly property int radius: 3
    readonly property int border: 1

    readonly property int iconSize: 16
    readonly property int transportIconSize: 20

    // The one non-token metric this prototype had to invent, kept here so it
    // is as visible as the frozen ones. ADR 0006 says "about three pixels".
    readonly property int minimumRangeWidth: 3

    function icon(name, color) {
        return "image://icon/" + name + "?color=" + encodeURIComponent(color)
    }
}
