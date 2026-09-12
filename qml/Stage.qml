import QtQuick
import "."

/*
  The video ground: the darkest surface in the window, so that once a frame is
  compositing into it the frame is the brightest thing on screen.

  The `VideoOutput`, the selected-Clip readout and the Pending Clip indicator
  arrive with the tickets that own them. What this carries today is the
  surface itself, which is what an empty workspace has to show.
*/
Rectangle {
    id: root

    color: Theme.stage
}
