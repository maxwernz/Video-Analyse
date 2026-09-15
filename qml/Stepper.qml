import QtQuick
import "."

/* A hundred-millisecond nudge. Held down, it repeats. */
Item {
    id: root

    property bool up: true
    signal triggered()

    Rectangle {
        anchors.fill: parent
        color: area.pressed ? Theme.control
                            : (area.containsMouse ? Theme.controlHover : Theme.control)
        border.width: Theme.border
        border.color: Theme.controlBorder
        radius: Theme.editorStepperRadius
    }

    Canvas {
        anchors.centerIn: parent
        width: Theme.editorStepperArrowWidth
        height: Theme.editorStepperArrowHeight
        onPaint: {
            var context = getContext("2d")
            context.reset()
            context.strokeStyle = area.containsMouse ? Theme.text : Theme.textMuted
            context.lineWidth = Theme.editorStepperArrowWeight
            context.lineCap = "round"
            context.lineJoin = "round"
            var left = 0.5
            var right = width - 0.5
            var middle = width / 2
            context.beginPath()
            if (root.up) {
                context.moveTo(left, height - 1)
                context.lineTo(middle, 1)
                context.lineTo(right, height - 1)
            } else {
                context.moveTo(left, 1)
                context.lineTo(middle, height - 1)
                context.lineTo(right, 1)
            }
            context.stroke()
        }

        Connections {
            target: area
            function onContainsMouseChanged() { parent.requestPaint() }
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onPressed: root.triggered()
        onPressAndHold: repeater.start()
        onReleased: repeater.stop()
        onCanceled: repeater.stop()
    }

    Timer {
        id: repeater
        interval: Theme.editorStepperRepeatMs
        repeat: true
        onTriggered: root.triggered()
    }
}
