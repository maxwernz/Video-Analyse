import QtQuick
import "."

/*
  An Analysis with no Source videos is still the workspace, not a welcome
  screen — the sidebar tabs are simply empty. What the stage carries is a
  designed drop target. A flat black rectangle is not an acceptable first
  impression, and it was the first thing the shipped interface showed.
*/
Rectangle {
    id: root

    signal addRequested()

    color: Theme.stage

    Item {
        anchors.centerIn: parent
        width: Math.min(parent.width - Theme.gutter * 4, 460)
        height: 260

        Rectangle {
            id: zone
            anchors.fill: parent
            radius: Theme.radius * 2
            color: dropArea.containsDrag || area.containsMouse
                   ? Qt.rgba(1, 1, 1, 0.022) : "transparent"

            // A dashed border, drawn rather than borrowed: Rectangle has no
            // dash pattern and this is the one place the design asks for one.
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var context = getContext("2d")
                    context.reset()
                    context.strokeStyle = dropArea.containsDrag ? Theme.accent : Theme.controlBorder
                    context.lineWidth = 1
                    context.setLineDash([5, 4])
                    context.strokeRect(0.5, 0.5, width - 1, height - 1)
                }
                Connections {
                    target: dropArea
                    function onContainsDragChanged() { parent.requestPaint() }
                }
            }
        }

        Column {
            anchors.centerIn: parent
            spacing: Theme.gutter
            width: parent.width - Theme.gutter * 2

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 40
                height: 40
                sourceSize.width: 80
                sourceSize.height: 80
                smooth: true
                source: Theme.icon("film-plus",
                                   dropArea.containsDrag ? Theme.accent : Theme.textFaint)
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
                    iconName: "film-plus"
                    onClicked: root.addRequested()
                }

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: shortcut.implicitWidth + 12
                        height: 20
                        radius: 2
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
        }

        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.addRequested()
        }

        DropArea {
            id: dropArea
            anchors.fill: parent
        }
    }
}
