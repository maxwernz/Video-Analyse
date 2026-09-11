import QtQuick
import "."

/*
  One transport row.

  Volume and mute left, one centred cluster, and the controls that act on the
  Analysis right, with the timecode pinned to the far right the way the
  Catapult reference pins it. The playback rate is a segmented control on
  purpose: in the captured evidence a stock QComboBox signalled "default Qt"
  more loudly than anything else in the window.
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

    // Left: mute.
    IconButton {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.gutter - 4
        iconName: workspace.muted ? "volume-off" : "volume"
        iconSize: Theme.transportIconSize
        size: 34
        tooltip: workspace.muted ? "Ton einschalten" : "Stummschalten"
        active: workspace.muted
        onClicked: workspace.toggleMuted()
    }

    // Centre: one cluster, play/pause larger than its neighbours.
    Row {
        anchors.centerIn: parent
        spacing: 2

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconName: "step-back"
            iconSize: Theme.transportIconSize
            size: 34
            tooltip: "Ein Bild zurück"
            onClicked: workspace.stepBackward()
        }

        SeekButton {
            anchors.verticalCenter: parent.verticalCenter
            forward: false
            tooltip: "Fünf Sekunden zurück"
            onClicked: workspace.jumpBackward()
        }

        Item {
            width: 46
            height: 46
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                radius: width / 2
                color: playArea.pressed ? Theme.control
                                        : (playArea.containsMouse ? Theme.controlHover : Theme.control)
                border.width: Theme.border
                border.color: Theme.controlBorder
            }

            Image {
                anchors.centerIn: parent
                anchors.horizontalCenterOffset: workspace.playing ? 0 : 1
                width: Theme.transportIconSize
                height: Theme.transportIconSize
                sourceSize.width: Theme.transportIconSize * 2
                sourceSize.height: Theme.transportIconSize * 2
                smooth: true
                source: Theme.icon(workspace.playing ? "pause" : "play", Theme.text)
            }

            MouseArea {
                id: playArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: workspace.playPause()
            }

            Tip { target: playArea; text: workspace.playing ? "Pause" : "Wiedergabe" }
        }

        SeekButton {
            anchors.verticalCenter: parent.verticalCenter
            forward: true
            tooltip: "Fünf Sekunden vor"
            onClicked: workspace.jumpForward()
        }

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconName: "step-forward"
            iconSize: Theme.transportIconSize
            size: 34
            tooltip: "Ein Bild vor"
            onClicked: workspace.stepForward()
        }
    }

    // Right: rate, the one primary action, and the timecode.
    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: Theme.gutter
        spacing: Theme.gap + 4

        SegmentedControl {
            anchors.verticalCenter: parent.verticalCenter
            // The Clip editor takes 360px out of this row, and marking a new
            // Clip while editing one is not a thing anybody wants to do.
            visible: workspace.mode !== "editing"
            options: workspace.playbackRates
            segmentWidth: 38
            currentIndex: workspace.playbackRateIndex
            onSelected: function (index) { workspace.setRateIndex(index) }
        }

        TextButton {
            anchors.verticalCenter: parent.verticalCenter
            visible: workspace.mode !== "editing"
            primary: true
            iconName: workspace.pendingActive ? "square" : "circle-dot"
            label: workspace.markActionText
            enabled: workspace.sourceCount > 0
            onClicked: workspace.markBoundary()
        }

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

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
