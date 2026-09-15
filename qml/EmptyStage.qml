import QtQuick
import "."

/*
  An Analysis with no Source videos is still the workspace, not a welcome
  screen. Its stage carries the prototype's designed invitation instead of a
  flat black rectangle.
*/
Rectangle {
    id: root

    objectName: "emptyStage"
    property bool containsDrag: false
    signal addRequested()

    color: Theme.stage

    Item {
        anchors.centerIn: parent
        width: Math.max(0, Math.min(parent.width - Theme.gutter * 4,
                                    Theme.emptyStageWidth))
        height: Math.min(parent.height, Theme.emptyStageHeight)

        Rectangle {
            id: zone
            anchors.fill: parent
            radius: Theme.radius * 2
            color: root.containsDrag || area.containsMouse
                   ? Theme.controlSubtleHover : "transparent"

            Canvas {
                id: borderCanvas
                anchors.fill: parent
                onPaint: {
                    var context = getContext("2d")
                    context.reset()
                    context.strokeStyle = root.containsDrag
                                          ? Theme.textMuted : Theme.controlBorder
                    context.lineWidth = Theme.border
                    context.setLineDash([Theme.emptyDashLength, Theme.emptyDashGap])
                    context.strokeRect(Theme.emptyBorderInset,
                                       Theme.emptyBorderInset,
                                       width - Theme.border,
                                       height - Theme.border)
                }
                Connections {
                    target: root
                    function onContainsDragChanged() { borderCanvas.requestPaint() }
                }
            }
        }

        Column {
            anchors.centerIn: parent
            spacing: Theme.gutter
            width: parent.width - Theme.gutter * 2

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Theme.emptyStageIconSize
                height: Theme.emptyStageIconSize
                sourceSize.width: Theme.emptyStageIconSize * 2
                sourceSize.height: Theme.emptyStageIconSize * 2
                smooth: true
                // The production Lucide set carries `file-video`; Prototype B's
                // hand-drawn `film-plus` is deliberately not promoted.
                source: Theme.icon("file-video",
                                   root.containsDrag ? Theme.text : Theme.textFaint)
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Video hinzufügen"
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeTitle
                font.weight: Theme.medium
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
                text: "Video hierher ziehen oder auswählen, um mit der Analyse zu beginnen."
                wrapMode: Text.WordWrap
                color: Theme.textMuted
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeBody
                font.weight: Theme.regular
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.gutter

                TextButton {
                    primary: true
                    label: "Video auswählen"
                    iconName: "file-video"
                    onClicked: root.addRequested()
                }

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: shortcut.implicitWidth + Theme.controlPadding
                    height: Theme.emptyShortcutHeight
                    radius: Theme.emptyShortcutRadius
                    color: Theme.control
                    border.width: Theme.border
                    border.color: Theme.controlBorder

                    Text {
                        id: shortcut
                        anchors.centerIn: parent
                        text: Qt.platform.os === "osx" ? "⌘⇧V" : "Strg+Umschalt+V"
                        color: Theme.textMuted
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeRuler
                        font.weight: Theme.medium
                    }
                }
            }
        }

        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.addRequested()
        }
    }
}
