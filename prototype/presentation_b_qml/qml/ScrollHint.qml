import QtQuick
import "."

/* A scrollbar that is only there while it is being used. */
Item {
    id: root
    property Flickable flickable

    Rectangle {
        parent: root.flickable
        visible: root.flickable && root.flickable.contentHeight > root.flickable.height
        opacity: root.flickable && root.flickable.moving ? 0.9 : 0.25
        Behavior on opacity { NumberAnimation { duration: 160 } }
        width: 3
        radius: 1.5
        color: Theme.controlBorder
        x: root.flickable ? root.flickable.width - width - 3 : 0
        y: root.flickable && root.flickable.contentHeight > 0
           ? root.flickable.contentY / root.flickable.contentHeight * root.flickable.height : 0
        height: root.flickable && root.flickable.contentHeight > 0
                ? Math.max(24, root.flickable.height / root.flickable.contentHeight * root.flickable.height) : 0
    }
}
