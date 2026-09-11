import QtQuick
import "."

/* A labelled control. `primary` is the one accent use an interface may make. */
Item {
    id: root

    property string label
    property string iconName
    property bool primary: false
    property bool enabled: true
    property int horizontalPadding: 12
    signal clicked()

    implicitHeight: Theme.controlHeight
    implicitWidth: row.implicitWidth + horizontalPadding * 2

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: {
            // A disabled primary gives the accent back. The accent has three
            // permitted uses and a control nobody can press is none of them.
            if (!root.enabled)
                return Theme.controlDisabled
            if (root.primary)
                return area.pressed ? Theme.accentPressed
                                    : (area.containsMouse ? Theme.accentHover : Theme.accent)
            return area.pressed ? Theme.control
                                : (area.containsMouse ? Theme.controlHover : Theme.control)
        }
        border.width: root.primary ? 0 : Theme.border
        border.color: Theme.controlBorder
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Image {
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            width: Theme.iconSize
            height: Theme.iconSize
            sourceSize.width: Theme.iconSize * 2
            sourceSize.height: Theme.iconSize * 2
            smooth: true
            source: root.iconName === "" ? "" : Theme.icon(root.iconName, text.color)
        }

        Text {
            id: text
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeBody
            font.weight: Theme.medium
            color: !root.enabled ? Theme.textFaint
                                 : (root.primary ? Theme.accentOn : Theme.text)
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
