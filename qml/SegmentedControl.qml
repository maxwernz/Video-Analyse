import QtQuick
import "."

/*
  One control, several exclusive choices, drawn as one object.

  The playback speed is the reason it exists: a stock combo box was the
  loudest "default Qt" signal in the captured evidence, and a segmented
  control shows the whole choice at once instead of hiding four values behind
  a chevron. Which option is current is not this control's decision — it draws
  whichever one the view model names.
*/
Item {
    id: root

    property var options: []
    property int currentIndex: 0
    property int segmentWidth: 0
    property int horizontalPadding: Theme.controlPadding
    signal selected(int index)

    implicitHeight: Theme.controlHeight
    implicitWidth: layout.implicitWidth + Theme.border * 2

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
        anchors.margins: Theme.border

        Repeater {
            model: root.options

            Item {
                required property int index
                required property var modelData

                width: root.segmentWidth > 0
                       ? root.segmentWidth
                       : Math.max(label.implicitWidth + root.horizontalPadding * 2,
                                  Theme.controlHeight + Theme.controlPadding)
                height: layout.height

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius - Theme.border
                    color: index === root.currentIndex
                           ? Theme.controlHover
                           : (segment.containsMouse ? Theme.controlSubtleHover : "transparent")
                }

                // Selection is one of the accent's three permitted uses.
                Rectangle {
                    visible: index === root.currentIndex
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - Theme.segmentIndicatorInset
                    height: Theme.segmentIndicatorHeight
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
