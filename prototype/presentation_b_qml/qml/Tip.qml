import QtQuick
import "."

/* A hover tooltip. Chrome that recedes still has to be explainable. */
Item {
    id: root
    property MouseArea target
    property string text
    parent: root.target ? root.target : null
    visible: false

    Timer {
        id: delay
        interval: 550
        onTriggered: if (root.target && root.target.containsMouse && root.text) chip.visible = true
    }

    Connections {
        target: root.target
        function onContainsMouseChanged() {
            chip.visible = false
            if (root.target.containsMouse && root.text) delay.restart()
            else delay.stop()
        }
    }

    Rectangle {
        id: chip
        parent: root.target ? root.target : null
        visible: false
        z: 1000
        x: Math.round((root.target ? root.target.width : 0) / 2 - width / 2)
        y: -height - 6
        width: label.implicitWidth + 16
        height: 22
        radius: Theme.radius
        color: Theme.control
        border.width: Theme.border
        border.color: Theme.controlBorder

        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeLabel
            font.weight: Theme.regular
        }
    }
}
