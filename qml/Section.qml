import QtQuick
import "."

/* One block of the form: a label, its controls, and the rule that ends it. */
Item {
    id: root

    property string label
    property bool lastSection: false
    default property alias content: column.data

    implicitHeight: column.height + Theme.gutter * 2 + (lastSection ? 0 : Theme.border)

    Column {
        id: column
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.topMargin: Theme.gutter
        anchors.leftMargin: Theme.gutter
        anchors.rightMargin: Theme.gutter
        spacing: Theme.gap + Theme.unit / 2

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
