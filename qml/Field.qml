import QtQuick
import "."

/* A single-line field. Built rather than themed: a stock control that has been
   restyled to within one property of itself still reads as a stock control. */
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
        anchors.leftMargin: Theme.gap + Theme.unit / 2
        anchors.rightMargin: Theme.gap + Theme.unit / 2
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
        Keys.onReturnPressed: { root.edited(text); focus = false }

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
