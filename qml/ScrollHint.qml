import QtQuick
import "."

/*
  A scrollbar that is only there while it is being used.

  The captured evidence had an unstyled white scrollbar against charcoal,
  which is what happens when a list is given the platform's own. This one is
  drawn from the same primitives as everything else, stays out of the way of
  the list it belongs to, and is absent entirely when everything already fits.
*/
Item {
    id: root

    property Flickable flickable

    Rectangle {
        parent: root.flickable
        visible: root.flickable && root.flickable.contentHeight > root.flickable.height
        opacity: root.flickable && root.flickable.moving
                 ? Theme.scrollHintMovingOpacity
                 : Theme.scrollHintRestingOpacity
        Behavior on opacity {
            NumberAnimation { duration: Theme.scrollHintFadeMs }
        }

        width: Theme.scrollHintWidth
        radius: Theme.scrollHintRadius
        color: Theme.controlBorder
        x: root.flickable ? root.flickable.width - width - Theme.scrollHintInset : 0
        y: root.flickable && root.flickable.contentHeight > 0
           ? root.flickable.contentY / root.flickable.contentHeight * root.flickable.height
           : 0
        height: root.flickable && root.flickable.contentHeight > 0
                ? Math.max(Theme.scrollHintMinimumLength,
                           root.flickable.height / root.flickable.contentHeight
                           * root.flickable.height)
                : 0
    }
}
