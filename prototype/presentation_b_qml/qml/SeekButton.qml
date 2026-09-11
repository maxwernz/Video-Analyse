import QtQuick
import "."

/* The five-second jumps, drawn as the reference draws them: an arc with the
   number inside it, so the distance is on the control rather than in a menu. */
Item {
    id: root

    property bool forward: true
    property int seconds: 5
    property string tooltip
    signal clicked()

    implicitWidth: 34
    implicitHeight: 34

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: area.pressed ? Theme.control : (area.containsMouse ? Theme.controlHover : "transparent")
    }

    Image {
        id: arc
        anchors.centerIn: parent
        width: Theme.transportIconSize
        height: Theme.transportIconSize
        sourceSize.width: Theme.transportIconSize * 2
        sourceSize.height: Theme.transportIconSize * 2
        smooth: true
        source: Theme.icon(root.forward ? "rotate-cw" : "rotate-ccw",
                           area.containsMouse ? Theme.text : Theme.textMuted)
    }

    Text {
        anchors.centerIn: arc
        anchors.verticalCenterOffset: 1
        text: root.seconds
        color: area.containsMouse ? Theme.text : Theme.textMuted
        font.family: Theme.uiFamily
        font.pixelSize: 9
        font.weight: Theme.medium
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Tip { target: area; text: root.tooltip }
}
