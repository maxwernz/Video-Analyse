import QtQuick
import "."

/*
  One transport row.

  Volume and mute left, one centred cluster with play/pause drawn larger than
  its neighbours, and the timecode pinned to the far right in monospace the
  way the Catapult reference pins it. The playback speed is a segmented
  control on purpose: in the captured evidence a stock combo box signalled
  "default Qt" more loudly than anything else in the window.

  The mark-Clip action belongs in this row too, as the one accent-coloured
  primary, and arrives with the Pending Clip in #45.
*/
Rectangle {
    id: root

    implicitHeight: Theme.transportHeight
    color: Theme.app

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.border
        color: Theme.rule
    }

    // Left: the sound.
    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.gutter - Theme.unit
        spacing: Theme.gap

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            // The vendored Lucide names, which are not the prototype's spellings.
            iconName: workspace.muted ? "volume-x" : "volume-2"
            iconSize: Theme.transportIconSize
            size: Theme.transportButtonSize
            tooltip: workspace.muted ? "Ton einschalten" : "Stummschalten"
            active: workspace.muted
            enabled: workspace.hasVideo
            onClicked: workspace.toggleMuted()
        }

        VolumeSlider {
            anchors.verticalCenter: parent.verticalCenter
            value: workspace.muted ? 0 : workspace.volume
            enabled: workspace.hasVideo && !workspace.muted
            tooltip: "Lautstärke"
            onMoved: function (level) { workspace.setVolume(level) }
        }
    }

    // Centre: one cluster, play/pause larger than its neighbours.
    Row {
        anchors.centerIn: parent
        spacing: Theme.transportClusterSpacing

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconName: "step-back"
            iconSize: Theme.transportIconSize
            size: Theme.transportButtonSize
            tooltip: "Ein Bild zurück"
            enabled: workspace.hasVideo
            onClicked: workspace.stepBackward()
        }

        SeekButton {
            anchors.verticalCenter: parent.verticalCenter
            forward: false
            tooltip: "Fünf Sekunden zurück"
            enabled: workspace.hasVideo
            onClicked: workspace.jumpBackward()
        }

        Item {
            width: Theme.transportPlaySize
            height: Theme.transportPlaySize
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                anchors.fill: parent
                anchors.margins: Theme.transportPlayInset
                radius: width / 2
                color: !workspace.hasVideo
                       ? Theme.controlDisabled
                       : (playArea.containsMouse && !playArea.pressed ? Theme.controlHover
                                                                      : Theme.control)
                border.width: Theme.border
                border.color: Theme.controlBorder
            }

            Image {
                anchors.centerIn: parent
                // The play triangle's mass sits left of its bounding box.
                anchors.horizontalCenterOffset: workspace.playing ? 0 : Theme.playIconOffset
                width: Theme.transportIconSize
                height: Theme.transportIconSize
                sourceSize.width: Theme.transportIconSize * 2
                sourceSize.height: Theme.transportIconSize * 2
                smooth: true
                source: Theme.icon(workspace.playing ? "pause" : "play",
                                   workspace.hasVideo ? Theme.text : Theme.textFaint)
            }

            MouseArea {
                id: playArea
                anchors.fill: parent
                hoverEnabled: true
                enabled: workspace.hasVideo
                cursorShape: Qt.PointingHandCursor
                onClicked: workspace.playPause()
            }

            Tip { target: playArea; text: workspace.playing ? "Pause" : "Wiedergabe" }
        }

        SeekButton {
            anchors.verticalCenter: parent.verticalCenter
            forward: true
            tooltip: "Fünf Sekunden vor"
            enabled: workspace.hasVideo
            onClicked: workspace.jumpForward()
        }

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconName: "step-forward"
            iconSize: Theme.transportIconSize
            size: Theme.transportButtonSize
            tooltip: "Ein Bild vor"
            enabled: workspace.hasVideo
            onClicked: workspace.stepForward()
        }
    }

    // Right: the speed, and the one place a time is read from.
    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: Theme.gutter
        spacing: Theme.transportGroupSpacing

        SegmentedControl {
            anchors.verticalCenter: parent.verticalCenter
            options: workspace.playbackRates
            segmentWidth: Theme.rateSegmentWidth
            currentIndex: workspace.playbackRateIndex
            onSelected: function (index) { workspace.setRateIndex(index) }
        }

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.timecodeSpacing

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: workspace.positionText
                color: Theme.text
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeTimecode
                font.weight: Theme.medium
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "/"
                color: Theme.textFaint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeTimecode
                font.weight: Theme.regular
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: workspace.durationText
                color: Theme.textMuted
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeTimecode
                font.weight: Theme.regular
            }
        }
    }
}
