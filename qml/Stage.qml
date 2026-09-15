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

  The selected-Clip readout and the Pending Clip indicator arrive with the
  tickets that own them.
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
}
