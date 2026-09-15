import QtQuick
import "."

Item {
    id: root
    property string text
    property string placeholder
    property bool mono: false
    signal edited(string value)

    implicitHeight: Theme.controlHeight

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.control
        border.width: Theme.border
        border.color: input.activeFocus ? Theme.accent : Theme.controlBorder
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: Theme.gap
        anchors.rightMargin: Theme.gap
        verticalAlignment: TextInput.AlignVCenter
        clip: true
        text: root.text
        color: Theme.text
        selectionColor: Theme.accent
        selectedTextColor: Theme.accentOn
        font.family: root.mono ? Theme.monoFamily : Theme.uiFamily
        font.pixelSize: root.mono ? Theme.sizeTimecode : Theme.sizeBody
        font.weight: root.mono ? Theme.medium : Theme.regular
        onEditingFinished: root.edited(text)

        Text {
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            visible: input.text === "" && !input.activeFocus
            text: root.placeholder
            color: Theme.textFaint
            font: input.font
        }
    }
}
