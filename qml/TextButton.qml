import QtQuick
import "."

Item {
    id: root
    property string label
    property string iconName
    property bool primary: false
    property bool enabled: true
    signal clicked()

    implicitHeight: Theme.controlHeight
    implicitWidth: row.implicitWidth + Theme.controlPadding * 2

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: !root.enabled ? Theme.controlDisabled
             : root.primary ? (area.pressed ? Theme.accentPressed
                                            : area.containsMouse ? Theme.accentHover : Theme.accent)
             : area.pressed ? Theme.control
                            : area.containsMouse ? Theme.controlHover : Theme.control
        border.width: root.primary ? 0 : Theme.border
        border.color: Theme.controlBorder
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.gap
        Image {
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            width: Theme.iconSize
            height: Theme.iconSize
            source: visible ? Theme.icon(root.iconName, labelText.color) : ""
        }
        Text {
            id: labelText
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: !root.enabled ? Theme.textFaint : root.primary ? Theme.accentOn : Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeBody
            font.weight: Theme.medium
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
