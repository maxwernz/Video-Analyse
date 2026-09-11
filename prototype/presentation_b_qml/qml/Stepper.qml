import QtQuick
import "."

/* A hundred-millisecond nudge. Held down, it repeats. */
Item {
    id: root
    property bool up: true
    signal triggered()

    Rectangle {
        anchors.fill: parent
        color: area.pressed ? Theme.control : (area.containsMouse ? Theme.controlHover : Theme.control)
        border.width: Theme.border
        border.color: Theme.controlBorder
        radius: 2
    }

    Canvas {
        anchors.centerIn: parent
        width: 8
        height: 5
        onPaint: {
            var context = getContext("2d")
            context.reset()
            context.strokeStyle = area.containsMouse ? Theme.text : Theme.textMuted
            context.lineWidth = 1.25
            context.lineCap = "round"
            context.lineJoin = "round"
            context.beginPath()
            if (root.up) { context.moveTo(0.5, 4); context.lineTo(4, 1); context.lineTo(7.5, 4) }
            else { context.moveTo(0.5, 1); context.lineTo(4, 4); context.lineTo(7.5, 1) }
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
        onPressed: root.triggered()
        onPressAndHold: repeater.start()
        onReleased: repeater.stop()
        onCanceled: repeater.stop()
    }

    Timer {
        id: repeater
        interval: 70
        repeat: true
        onTriggered: root.triggered()
    }
}
