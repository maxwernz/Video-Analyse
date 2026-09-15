import QtQuick
import "."

/*
  The one seek surface, scoped to the Active Source video (ADR 0006).

  60px: a 16px ruler over a 44px track. The interaction grammar is the ADR's,
  unchanged:

    - pressing or dragging anywhere scrubs the playhead to that time,
      including on top of a Clip range;
    - clicking a Clip range additionally selects it, without moving the
      playhead to its start;
    - double-clicking a Clip range seeks to the Clip start.

  Ranges are Items, so the scene graph does the hit-testing. There is no
  JavaScript loop over Clips deciding what was clicked: `childAt` asks the
  renderer what is actually under the cursor, which also makes the three-pixel
  minimum width a hit target rather than only a drawing.

  Two things here are not the prototype's. Scrubbing goes through
  `scrubTo`/`endScrub` rather than `seek`, because the media player coalesces
  seeks past about twenty a second and the picture stops following the
  pointer; the rate lives in Python. And the playhead reads an interpolated
  position, so it moves between the sixteen positions a second the player
  reports instead of stepping through them.
*/
Item {
    id: root

    readonly property int durationMs: workspace.durationMs
    readonly property bool ready: durationMs > 0 && width > 0

    implicitHeight: Theme.timelineHeight

    function msToX(ms) {
        return ready ? (ms / durationMs) * width : 0
    }

    function xToMs(x) {
        return ready ? Math.round(Math.max(0, Math.min(width, x)) / width * durationMs) : 0
    }

    onWidthChanged: relayoutRuler()
    onDurationMsChanged: relayoutRuler()
    Component.onCompleted: relayoutRuler()

    function relayoutRuler() {
        workspace.layoutRuler(width, durationMs)
    }

    // --- Ruler ------------------------------------------------------------

    Rectangle {
        id: ruler
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: Theme.rulerHeight
        color: Theme.app

        Repeater {
            model: workspace.rulerModel

            Item {
                required property var model
                x: root.msToX(model.positionMs)
                height: ruler.height

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: Theme.border
                    height: model.major ? Theme.majorTickHeight : Theme.minorTickHeight
                    color: model.major ? Theme.controlBorder : Theme.rule
                }

                Text {
                    visible: model.label !== ""
                    y: 0
                    // The first and last labels turn inward so neither is
                    // half a label hanging off the end of the track.
                    x: root.msToX(model.positionMs) < Theme.rulerLabelTurnPx
                       ? Theme.rulerLabelGap
                       : (root.width - root.msToX(model.positionMs)
                          < implicitWidth + Theme.rulerLabelGap * 2
                          ? -implicitWidth - Theme.rulerLabelGap : Theme.rulerLabelGap)
                    text: model.label
                    color: Theme.textFaint
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.sizeRuler
                    font.weight: Theme.regular
                }
            }
        }
    }

    // --- Track ------------------------------------------------------------

    Rectangle {
        id: track
        anchors { top: ruler.bottom; left: parent.left; right: parent.right }
        height: Theme.trackHeight
        color: Theme.stage

        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: Theme.border
            color: Theme.rule
        }

        Item {
            id: rangesLayer
            anchors.fill: parent

            Repeater {
                model: workspace.rangeModel

                Item {
                    id: range
                    required property var model
                    property string clipId: model.clipId
                    property int startMs: model.startMs
                    // A Clip with no Category carries no colour of its own.
                    readonly property color tint: model.color === ""
                                                  ? Theme.textFaint : model.color

                    x: root.msToX(model.startMs)
                    width: Math.max(Theme.minimumRangeWidth,
                                    root.msToX(model.endMs) - root.msToX(model.startMs))
                    y: 0
                    height: track.height

                    // The Category colour at 40% alpha over the stage.
                    Rectangle {
                        anchors.fill: parent
                        color: Theme.rangeFill(range.tint, range.model.selected)
                    }

                    // 1px full-colour top edge.
                    Rectangle {
                        anchors { top: parent.top; left: parent.left; right: parent.right }
                        height: Theme.border
                        color: range.tint
                    }

                    // Selection is brightening plus an outline: a treatment that
                    // still reads when two Categories are close in colour.
                    Rectangle {
                        anchors.fill: parent
                        visible: range.model.selected
                        color: "transparent"
                        border.width: Theme.border
                        border.color: Theme.rangeOutline(range.tint)
                    }
                }
            }
        }
    }

    // --- Hover ------------------------------------------------------------

    Rectangle {
        id: cursorLine
        visible: area.containsMouse && !area.pressed && root.ready
        x: Math.round(area.mouseX)
        y: 0
        width: Theme.border
        height: root.height
        color: Theme.textFaint
    }

    Rectangle {
        id: hoverTip
        visible: cursorLine.visible
        z: Theme.tooltipLayer
        height: Theme.tooltipHeight
        width: hoverText.implicitWidth + Theme.controlPadding
        y: -height - Theme.tooltipOffset
        x: Math.round(Math.max(0, Math.min(root.width - width, area.mouseX - width / 2)))
        radius: Theme.radius
        color: Theme.control
        border.width: Theme.border
        border.color: Theme.controlBorder

        Text {
            id: hoverText
            anchors.centerIn: parent
            text: workspace.timeText(root.xToMs(area.mouseX))
            color: Theme.text
            font.family: Theme.monoFamily
            font.pixelSize: Theme.sizeTimecode
            font.weight: Theme.medium
        }
    }

    // --- Playhead ---------------------------------------------------------

    Item {
        id: playhead
        visible: root.ready
        z: Theme.playheadLayer
        x: Math.round(root.msToX(workspace.positionMs))
        y: 0
        width: Theme.playheadWidth
        height: root.height

        Rectangle {
            anchors.fill: parent
            color: Theme.accent
        }

        // The grabbable handle sits in the ruler, where the ADR put it.
        readonly property bool grabbable: area.containsMouse
                                          && Math.abs(area.mouseX - playhead.x)
                                             < Theme.playheadGrabPx

        Rectangle {
            id: handle
            x: -(Theme.playheadHandleWidth - Theme.playheadWidth) / 2
            y: 0
            width: Theme.playheadHandleWidth
            height: Theme.rulerHeight - Theme.border * 2
            radius: Theme.playheadHandleRadius
            color: area.pressed ? Theme.accentPressed
                                : (playhead.grabbable ? Theme.accentHover : Theme.accent)
        }
    }

    // --- Interaction ------------------------------------------------------

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        z: Theme.interactionLayer

        function rangeUnder(x) {
            return rangesLayer.childAt(x, track.height / 2)
        }

        onPressed: function (mouse) {
            workspace.scrubTo(root.xToMs(mouse.x))
            var hit = rangeUnder(mouse.x)
            if (hit && hit.clipId !== undefined)
                workspace.selectClip(hit.clipId)
        }

        onPositionChanged: function (mouse) {
            if (pressed)
                workspace.scrubTo(root.xToMs(mouse.x))
        }

        onReleased: workspace.endScrub()

        onDoubleClicked: function (mouse) {
            var hit = rangeUnder(mouse.x)
            if (hit && hit.startMs !== undefined)
                workspace.seek(hit.startMs)
        }
    }
}
