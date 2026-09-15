import QtQuick
import "."

/*
  A Clip boundary.

  Sized for a whole timecode, because the captured evidence shows the previous
  field clipped to ':00.000' and a coach cannot check a boundary they cannot
  read. Editing one scrubs the video to that frame: the number is only worth
  trusting if the frame it names is on screen while it is being typed.
*/
Item {
    id: root

    property string label
    property string value
    property string which: "start"

    implicitHeight: Theme.editorBoundaryHeight

    Text {
        id: caption
        anchors.top: parent.top
        anchors.left: parent.left
        text: root.label
        color: Theme.textMuted
        font.family: Theme.uiFamily
        font.pixelSize: Theme.sizeLabel
        font.weight: Theme.medium
    }

    IconButton {
        id: takeButton
        anchors.verticalCenter: caption.verticalCenter
        anchors.right: parent.right
        size: Theme.editorTakeButtonSize
        iconSize: Theme.editorTakeIconSize
        iconName: "circle-dot"
        tooltip: "Auf die aktuelle Position setzen"
        onClicked: workspace.takeDraftBoundaryFromPlayhead(root.which)
    }

    Field {
        id: field
        anchors { left: parent.left; right: steppers.left; bottom: parent.bottom }
        anchors.rightMargin: Theme.gap - Theme.unit / 2
        mono: true
        text: root.value
        onEdited: function (value) {
            if (root.which === "start") workspace.setDraftStartText(value)
            else workspace.setDraftEndText(value)
        }
    }

    Column {
        id: steppers
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: Theme.editorStepperWidth
        height: Theme.controlHeight
        spacing: 0

        Stepper {
            width: parent.width
            height: parent.height / 2
            up: true
            onTriggered: workspace.nudgeDraftBoundary(root.which, Theme.boundaryNudgeMs)
        }

        Stepper {
            width: parent.width
            height: parent.height / 2
            up: false
            onTriggered: workspace.nudgeDraftBoundary(root.which, -Theme.boundaryNudgeMs)
        }
    }
}
