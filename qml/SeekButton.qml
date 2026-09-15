import QtQuick
import "."

/* The five-second jumps, drawn as the reference draws them: an arc with the
   number inside it, so the distance is on the control rather than in a menu. */
Item {
    id: root

    property bool forward: true
    property int seconds: 5
    property string tooltip
    property bool enabled: true
    signal clicked()

    implicitWidth: Theme.transportButtonSize
    implicitHeight: Theme.transportButtonSize

    readonly property color contentColor: !root.enabled
                                          ? Theme.textFaint
                                          : (area.containsMouse ? Theme.text : Theme.textMuted)

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: !root.enabled
               ? "transparent"
               : (area.pressed ? Theme.control
                               : (area.containsMouse ? Theme.controlHover : "transparent"))
    }

    Image {
        id: arc
        anchors.centerIn: parent
        width: Theme.transportIconSize
        height: Theme.transportIconSize
        sourceSize.width: Theme.transportIconSize * 2
        sourceSize.height: Theme.transportIconSize * 2
        smooth: true
        source: Theme.icon(root.forward ? "rotate-cw" : "rotate-ccw", root.contentColor)
    }

    Text {
        anchors.centerIn: arc
        anchors.verticalCenterOffset: Theme.seekLabelOffset
        text: root.seconds
        color: root.contentColor
        font.family: Theme.uiFamily
        font.pixelSize: Theme.seekLabelSize
        font.weight: Theme.medium
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Tip { target: area; text: root.tooltip }
}
