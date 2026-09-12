import QtQuick
import "."

/*
  The left sidebar: the `panel` surface, and later a segmented control over the
  Clip list and the Source-video list.

  There will be no column header. A spreadsheet header strip is not something a
  coach reads, and in the captured evidence it was what truncated the
  Source-video column at the default sidebar width. The lists themselves are
  #45's work; an empty workspace has nothing to put in them.
*/
Rectangle {
    id: root

    color: Theme.panel
}
