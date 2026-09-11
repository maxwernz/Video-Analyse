import QtQuick
import "."

/*
  One control, several exclusive choices, drawn as one object.

  The sidebar tabs and the playback rate both use it. The rate control is the
  reason it exists: a stock combo box was the loudest "default Qt" signal in
  the captured evidence, and a segmented control shows the whole choice at
  once instead of hiding four values behind a chevron.
*/
Item {
    id: root

    property var options: []
    property int currentIndex: 0
    property int segmentWidth: 0
    property int horizontalPadding: 12
    signal selected(int index)

    implicitHeight: Theme.controlHeight
    implicitWidth: layout.implicitWidth + 2

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.control
        border.width: Theme.border
        border.color: Theme.controlBorder
    }

    Row {
        id: layout
        anchors.fill: parent
        anchors.margins: 1

        Repeater {
            model: root.options

            Item {
                required property int index
                required property var modelData

                width: root.segmentWidth > 0
                       ? root.segmentWidth
                       : Math.max(label.implicitWidth + root.horizontalPadding * 2, 40)
                height: layout.height

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius - 1
                    color: index === root.currentIndex
                           ? Theme.controlHover
                           : (segment.containsMouse ? Qt.rgba(1, 1, 1, 0.03) : "transparent")
                }

                // Selection is one of the accent's three permitted uses.
                Rectangle {
                    visible: index === root.currentIndex
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 12
                    height: 2
                    color: Theme.accent
                }

                Text {
                    id: label
                    anchors.centerIn: parent
                    text: modelData
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: index === root.currentIndex ? Theme.medium : Theme.regular
                    color: index === root.currentIndex ? Theme.text : Theme.textMuted
                }

                MouseArea {
                    id: segment
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selected(index)
                }
            }
        }
    }
}
