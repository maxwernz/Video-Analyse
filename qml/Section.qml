import QtQuick
import "."

Item {
    id: root
    property string label
    property bool lastSection: false
    default property alias content: column.data

    implicitHeight: column.height + Theme.gutter * 2 + (lastSection ? 0 : Theme.border)

    Column {
        id: column
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.margins: Theme.gutter
        spacing: Theme.gap
        Text {
            text: root.label
            color: Theme.textMuted
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeLabel
            font.weight: Theme.medium
        }
    }

    Rectangle {
        visible: !root.lastSection
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: Theme.border
        color: Theme.rule
    }
}
