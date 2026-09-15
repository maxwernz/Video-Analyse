import QtQuick
import "."

/*
  The volume level, beside mute.

  The transport was always specified as "volume and mute", and the level is a
  different act from the switch: turning the bench audio down is not silencing
  it. The prototype could only draw the switch, because the player seam had no
  level to bind to; it has one now.

  The accent is not used here. It is reserved for the playhead, the primary
  action and selection, and a volume level is none of the three.
*/
Item {
    id: root

    property real value: 1.0
    property bool enabled: true
    property string tooltip
    signal moved(real value)

    implicitWidth: Theme.volumeSliderWidth
    implicitHeight: Theme.controlHeight

    readonly property real fraction: Math.max(0, Math.min(1, root.value))
    readonly property color levelColor: !root.enabled
                                        ? Theme.textFaint
                                        : (area.containsMouse || area.pressed ? Theme.text
                                                                              : Theme.textMuted)

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.volumeKnobSize / 2
        anchors.rightMargin: Theme.volumeKnobSize / 2
        height: Theme.volumeTrackHeight
        radius: height / 2
        color: Theme.control
        border.width: Theme.border
        border.color: Theme.controlBorder
    }

    Rectangle {
        anchors.verticalCenter: track.verticalCenter
        x: track.x
        width: track.width * root.fraction
        height: track.height
        radius: track.radius
        color: root.levelColor
    }

    Rectangle {
        anchors.verticalCenter: track.verticalCenter
        x: track.x + track.width * root.fraction - width / 2
        width: Theme.volumeKnobSize
        height: Theme.volumeKnobSize
        radius: width / 2
        color: root.levelColor
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor

        function report(x) {
            if (track.width <= 0)
                return
            root.moved(Math.max(0, Math.min(1, (x - track.x) / track.width)))
        }

        onPressed: function (mouse) { report(mouse.x) }
        onPositionChanged: function (mouse) { if (pressed) report(mouse.x) }
    }

    Tip { target: area; text: root.tooltip }
}
