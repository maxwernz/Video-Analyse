import QtQuick
import "."

/*
  The left sidebar: a segmented control over two lists.

  There is no column header. A spreadsheet header strip is not something a
  coach reads, and in the captured evidence it was what truncated the
  Source-video column at the default sidebar width.

  Both lists are given finished rows. The grouping, the ordering, the
  timecodes and the Source-video badge are decided in Python, so the only
  arithmetic here is the one thing only the running window knows: how wide
  the sidebar actually is, and therefore whether a Clip's length still fits
  beside its title. Which field gives way when it does not is a recorded
  decision (`docs/design/visual-tokens.md`, Source-video cue), carried here
  as one token rather than as a judgement made in a delegate.
*/
Rectangle {
    id: root

    color: Theme.panel

    // Segmented control, not underlined web-style tabs.
    Item {
        id: tabs
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.margins: Theme.gutter
        anchors.bottomMargin: 0
        height: Theme.controlHeight

        SegmentedControl {
            anchors.fill: parent
            options: ["Clips", "Videos"]
            segmentWidth: Math.floor((parent.width - Theme.border * 2) / 2)
            currentIndex: workspace.sidebarTab === "clips" ? 0 : 1
            onSelected: function (index) {
                workspace.setSidebarTab(index === 0 ? "clips" : "videos")
            }
        }
    }

    Rectangle {
        id: tabsRule
        anchors {
            top: tabs.bottom
            topMargin: Theme.gutter - Theme.unit
            left: parent.left
            right: parent.right
        }
        height: Theme.border
        color: Theme.rule
    }

    // --- Clips ------------------------------------------------------------

    ListView {
        id: clipList
        objectName: "clipList"
        anchors { top: tabsRule.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: workspace.sidebarTab === "clips"
        clip: true
        model: workspace.clipModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollHint { flickable: clipList }

        // One delegate, two shapes. A Loader would recycle its item out from
        // under these bindings and spend the first frame reading a null model.
        delegate: Item {
            id: rowItem
            required property var model
            required property int index

            width: clipList.width
            height: model.kind === "category" ? Theme.categoryHeaderHeight
                                              : Theme.clipRowHeight

            // --- Category heading ---
            Item {
                anchors.fill: parent
                visible: rowItem.model.kind === "category"

                Rectangle {
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    anchors.leftMargin: Theme.gutter
                    anchors.rightMargin: Theme.gutter
                    height: Theme.border
                    color: Theme.rule
                    visible: rowItem.index !== 0
                }

                Rectangle {
                    id: dot
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.gutter
                    width: Theme.categoryDotSize
                    height: Theme.categoryDotSize
                    radius: Theme.categoryDotSize / 2
                    color: rowItem.model.categoryColor === ""
                           ? Theme.textFaint : rowItem.model.categoryColor
                }

                Text {
                    anchors.verticalCenter: dot.verticalCenter
                    anchors.left: dot.right
                    anchors.leftMargin: Theme.gap
                    text: rowItem.model.title
                    color: Theme.textMuted
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeLabel
                    font.weight: Theme.medium
                }

                Text {
                    anchors.verticalCenter: dot.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.gutter
                    text: rowItem.model.count
                    color: Theme.textFaint
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.sizeRuler
                    font.weight: Theme.regular
                }
            }

            // --- Clip row ---
            Item {
                anchors.fill: parent
                visible: rowItem.model.kind === "clip"

                Rectangle {
                    anchors.fill: parent
                    color: rowItem.model.selected
                           ? Theme.selection
                           : (rowArea.containsMouse ? Theme.controlSubtleHover
                                                    : "transparent")
                }

                // The 3px full-colour Category bar at the leading edge.
                Rectangle {
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                    width: Theme.clipCategoryBarWidth
                    color: rowItem.model.categoryColor === ""
                           ? Theme.textFaint : rowItem.model.categoryColor
                }

                Text {
                    id: title
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.clipTitleInset
                    anchors.right: badge.visible ? badge.left : times.left
                    anchors.rightMargin: Theme.clipTitleGap
                    text: rowItem.model.title
                    elide: Text.ElideRight
                    color: Theme.text
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeRow
                    font.weight: Theme.medium
                }

                // The Source-video cue, shown only in a multi-video Analysis.
                Rectangle {
                    id: badge
                    visible: rowItem.model.sourceBadge !== ""
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: times.left
                    anchors.rightMargin: Theme.badgeGap
                    width: badgeText.implicitWidth + Theme.badgePadding
                    height: Theme.badgeHeight
                    radius: Theme.badgeRadius
                    color: Theme.control
                    border.width: Theme.border
                    border.color: Theme.controlBorder

                    Text {
                        id: badgeText
                        anchors.centerIn: parent
                        text: rowItem.model.sourceBadge
                        color: Theme.textMuted
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeRuler
                        font.weight: Theme.medium
                    }
                }

                // Start and length, right-aligned, tabular, so the columns
                // line up down the list however long the titles are.
                Row {
                    id: times
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.gutter
                    spacing: Theme.timecodeColumnSpacing

                    Text {
                        text: rowItem.model.startText
                        color: Theme.text
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeTimecode
                        font.weight: Theme.medium
                    }

                    Text {
                        // The one field the row gives up when the sidebar is
                        // too narrow to carry all four.
                        visible: root.width >= Theme.clipDurationMinimumWidth
                        width: Theme.durationColumnWidth
                        horizontalAlignment: Text.AlignRight
                        text: rowItem.model.durationText
                        color: Theme.textMuted
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeTimecode
                        font.weight: Theme.regular
                    }
                }

                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    // One action: the Clip's Source video becomes the active
                    // one and the player goes to the Clip's start.
                    onClicked: workspace.navigateToClip(rowItem.model.clipId)
                }

                // The badge is two characters; the whole name is one hover away.
                Tip { target: rowArea; text: rowItem.model.sourceCue }
            }
        }
    }

    // --- Videos -----------------------------------------------------------

    ListView {
        id: videoList
        objectName: "videoList"
        anchors { top: tabsRule.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: workspace.sidebarTab === "videos"
        clip: true
        model: workspace.sourceModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollHint { flickable: videoList }

        delegate: Item {
            id: videoItem
            required property var model

            width: videoList.width
            height: Theme.sourceRowHeight

            Rectangle {
                anchors.fill: parent
                color: videoItem.model.active
                       ? Theme.selection
                       : (videoArea.containsMouse ? Theme.controlSubtleHover
                                                  : "transparent")
            }

            // The Active Source video is a selection, and selection is one of
            // the accent's three permitted uses.
            Rectangle {
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: Theme.clipCategoryBarWidth
                color: Theme.accent
                visible: videoItem.model.active
            }

            Image {
                id: filmIcon
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.gutter
                width: Theme.iconSize
                height: Theme.iconSize
                sourceSize.width: Theme.iconSize * 2
                sourceSize.height: Theme.iconSize * 2
                smooth: true
                source: Theme.icon("film", videoItem.model.active ? Theme.text
                                                                  : Theme.textMuted)
            }

            Text {
                id: videoName
                anchors {
                    left: filmIcon.right
                    leftMargin: Theme.sourceRowIconGap
                    right: parent.right
                    rightMargin: Theme.gutter
                    top: parent.top
                    topMargin: Theme.sourceRowNameTop
                }
                // A file name is told apart by its end as much as its start,
                // so what goes is the middle.
                text: videoItem.model.name
                elide: Text.ElideMiddle
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeRow
                font.weight: Theme.medium
            }

            Row {
                anchors {
                    left: videoName.left
                    top: videoName.bottom
                    topMargin: Theme.sourceRowLineGap
                }
                spacing: Theme.gap

                Text {
                    text: videoItem.model.durationText
                    color: Theme.textFaint
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.sizeTimecode
                    font.weight: Theme.medium
                }

                Text {
                    text: "·  " + videoItem.model.clipCountText
                    color: Theme.textFaint
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Theme.regular
                }
            }

            MouseArea {
                id: videoArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: workspace.selectSourceVideo(videoItem.model.sourceId)
            }
        }
    }

    // Right-edge hairline between the sidebar and the video area.
    Rectangle {
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: Theme.border
        color: Theme.rule
    }
}
