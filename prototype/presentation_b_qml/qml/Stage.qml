import QtQuick
import QtMultimedia
import "."

/*
  The video ground: the darkest surface in the window, so the frame is the
  brightest thing on screen.

  The video renders into the Qt Quick scene graph through a real VideoOutput,
  attached to the existing Python playback seam. `stillSource` exists only for
  headless capture, where there is no GPU to composite a frame — it is never
  the answer to the video-surface question, and the prototype says so.
*/
Rectangle {
    id: root

    property string stillSource: ""

    color: Theme.stage

    VideoOutput {
        id: output
        anchors.fill: parent
        anchors.margins: 0
        fillMode: VideoOutput.PreserveAspectFit
        visible: root.stillSource === ""
        Component.onCompleted: workspace.attachVideoOutput(output)
    }

    Image {
        anchors.fill: parent
        visible: root.stillSource !== ""
        source: root.stillSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    // The selected Clip, named where the timeline can be read at the same time.
    Rectangle {
        id: readout
        visible: workspace.hasSelection && workspace.mode !== "editing"
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: Theme.gutter
        width: readoutRow.implicitWidth + Theme.gutter * 2
        height: 30
        radius: Theme.radius
        color: Qt.rgba(0, 0, 0, 0.62)
        border.width: Theme.border
        border.color: Qt.rgba(1, 1, 1, 0.08)

        Row {
            id: readoutRow
            anchors.centerIn: parent
            spacing: Theme.gap

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: workspace.selectedClipTitle
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeRow
                font.weight: Theme.medium
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: workspace.selectedClipRange
                color: Theme.textMuted
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeTimecode
                font.weight: Theme.regular
            }
        }
    }

    // A Pending Clip is a state the window must not be able to forget it is in.
    Rectangle {
        visible: workspace.pendingActive
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.gutter
        width: pendingRow.implicitWidth + Theme.gutter * 2
        height: 30
        radius: Theme.radius
        color: Qt.rgba(0, 0, 0, 0.62)
        border.width: Theme.border
        border.color: Qt.rgba(1, 1, 1, 0.12)

        Row {
            id: pendingRow
            anchors.centerIn: parent
            spacing: Theme.gap

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 7; height: 7; radius: 3.5
                color: Theme.text
                SequentialAnimation on opacity {
                    running: workspace.pendingActive
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.25; duration: 700; easing.type: Easing.InOutQuad }
                    NumberAnimation { to: 1.0;  duration: 700; easing.type: Easing.InOutQuad }
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: workspace.pendingText
                color: Theme.text
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeTimecode
                font.weight: Theme.medium
            }
        }
    }
}
