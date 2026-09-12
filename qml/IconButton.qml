import QtQuick
import "."

/* A square icon control. The whole family recolours through one provider. */
Item {
    id: root

    property string iconName
    property string tooltip
    property bool active: false
    property bool enabled: true
    property int size: Theme.controlHeight
    property int iconSize: Theme.iconSize
    property bool flat: true
    property color iconColor: !enabled ? Theme.textFaint
                                       : (active || area.containsMouse ? Theme.text
                                                                       : Theme.textMuted)
    signal clicked()

    implicitWidth: size
    implicitHeight: size

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: !root.enabled ? "transparent"
                             : (area.pressed ? Theme.control
                                             : (area.containsMouse || root.active ? Theme.controlHover
                                                                                  : "transparent"))
        border.width: root.flat ? 0 : Theme.border
        border.color: Theme.controlBorder
    }

    Image {
        anchors.centerIn: parent
        width: root.iconSize
        height: root.iconSize
        sourceSize.width: root.iconSize * 2
        sourceSize.height: root.iconSize * 2
        smooth: true
        // A control with no icon named yet asks the provider for nothing. The
        // prototype asked for the empty name, which the engine reports as an
        // image it could not decode.
        source: root.iconName === "" ? "" : Theme.icon(root.iconName, root.iconColor)
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
