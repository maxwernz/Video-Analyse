import QtQuick
import QtMultimedia
import "."

/*
  The video ground: the darkest surface in the window, so that the frame
  compositing into it is the brightest thing on screen.

  The video renders into the Qt Quick scene graph through a real
  `VideoOutput`, handed to the existing Python playback seam unmodified:
  `Playback.set_video_output` takes a plain `QObject`, and a `VideoOutput`
  carries the `videoSink` that `QMediaPlayer` looks for.

  The Pending Clip is shown here, over the picture, because it is a state the
  window must not be able to forget it is in: one boundary marked and the
  other one owed. The selected-Clip readout arrives with the ticket that owns
  it.
*/
Rectangle {
    id: root

    color: Theme.stage

    VideoOutput {
        id: output
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectFit
        Component.onCompleted: workspace.attachVideoOutput(output)
    }

    Rectangle {
        id: pending

        visible: workspace.pendingActive
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.gutter
        width: pendingRow.implicitWidth + Theme.gutter * 2
        height: Theme.pendingBadgeHeight
        radius: Theme.radius
        color: Theme.pendingScrim
        border.width: Theme.border
        border.color: Theme.pendingScrimBorder

        Row {
            id: pendingRow
            anchors.centerIn: parent
            spacing: Theme.gap

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: Theme.pendingDotSize
                height: Theme.pendingDotSize
                radius: Theme.pendingDotSize / 2
                color: Theme.text

                SequentialAnimation on opacity {
                    running: workspace.pendingActive
                    loops: Animation.Infinite
                    NumberAnimation {
                        to: Theme.pendingBlinkOpacity
                        duration: Theme.pendingBlinkMs
                        easing.type: Easing.InOutQuad
                    }
                    NumberAnimation {
                        to: 1.0
                        duration: Theme.pendingBlinkMs
                        easing.type: Easing.InOutQuad
                    }
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
