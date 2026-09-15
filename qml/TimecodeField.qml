import QtQuick
import "."

Item {
    id: root
    property string label
    property string value
    property string which

    implicitHeight: Theme.editorBoundaryHeight

    Text {
        id: caption
        anchors { top: parent.top; left: parent.left }
        text: root.label
        color: Theme.textMuted
        font.family: Theme.uiFamily
        font.pixelSize: Theme.sizeLabel
        font.weight: Theme.medium
    }

    IconButton {
        anchors { verticalCenter: caption.verticalCenter; right: parent.right }
        size: Theme.iconSize
        iconSize: Theme.sizeLabel
        iconName: "circle-dot"
        tooltip: "Auf die aktuelle Position setzen"
        onClicked: workspace.takeDraftBoundaryFromPlayhead(root.which)
    }

    Field {
        anchors { left: parent.left; right: steppers.left; bottom: parent.bottom }
        anchors.rightMargin: Theme.unit
        mono: true
        text: root.value
        onEdited: function (editedValue) {
            if (root.which === "start") workspace.setDraftStartText(editedValue)
            else workspace.setDraftEndText(editedValue)
        }
    }

    Column {
        id: steppers
        anchors { right: parent.right; bottom: parent.bottom }
        width: Theme.editorStepperWidth
        height: Theme.controlHeight
        Repeater {
            model: [100, -100]
            Rectangle {
                required property int modelData
                width: steppers.width
                height: steppers.height / 2
                color: stepArea.containsMouse ? Theme.controlHover : Theme.control
                border.width: Theme.border
                border.color: Theme.controlBorder
                Text {
                    anchors.centerIn: parent
                    text: parent.modelData > 0 ? "+" : "−"
                    color: Theme.textMuted
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.sizeLabel
                }
                MouseArea {
                    id: stepArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: workspace.nudgeDraftBoundary(root.which, parent.modelData)
                }
            }
        }
    }
}
