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

    CategoryManager {
        anchors.fill: parent
        z: Theme.menuLayer
    }

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
        focus: visible
        clip: true
        model: workspace.sourceModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollHint { flickable: videoList }

        Keys.onDownPressed: function (event) {
            if (videoList.currentIndex >= videoList.count - 1)
                return
            videoList.currentIndex += 1
            workspace.selectSourceVideo(videoList.currentItem.sourceId)
            event.accepted = true
        }

        Keys.onUpPressed: function (event) {
            if (videoList.currentIndex <= 0)
                return
            videoList.currentIndex -= 1
            workspace.selectSourceVideo(videoList.currentItem.sourceId)
            event.accepted = true
        }

        delegate: Item {
            id: videoItem
            required property var model
            required property int index
            property string sourceId: videoItem.model.sourceId
            property bool renaming: false
            // Armed by a first click on the remove control; a second click
            // within the window confirms it. Left this way by any other
            // interaction, so a stray click can never remove a video.
            property bool removeArmed: false

            width: videoList.width
            height: Theme.sourceRowHeight

            Timer {
                id: disarmTimer
                interval: 3000
                onTriggered: videoItem.removeArmed = false
            }

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
                visible: videoItem.model.available
                source: Theme.icon("film", videoItem.model.active ? Theme.text
                                                                  : Theme.textMuted)
            }

            // Unavailability is a display state, not an error: the row still
            // reads and still offers Relink, it just cannot show a frame for
            // a Source video nothing currently backs.
            Image {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.gutter
                width: Theme.iconSize
                height: Theme.iconSize
                sourceSize.width: Theme.iconSize * 2
                sourceSize.height: Theme.iconSize * 2
                smooth: true
                visible: !videoItem.model.available
                source: Theme.icon("triangle-alert", Theme.warning)
            }

            // The full-row hit target for selecting this Source video.
            // Declared before `videoName`, so a later sibling's own input
            // handling — the rename text's double-click, `rowActions`'
            // buttons — sits above it for the region each one covers, the
            // same stacking rule `rowActions` below relies on.
            MouseArea {
                id: videoArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    videoList.currentIndex = videoItem.index
                    workspace.selectSourceVideo(videoItem.model.sourceId)
                }
            }

            // What an armed removal will take with it, in the row itself
            // rather than a tooltip: the two-click confirmation has no hover
            // dwell for a tooltip to appear during, so the Clip count has to
            // be something the analyst is already looking at.
            Text {
                id: removeWarning
                visible: videoItem.removeArmed
                anchors {
                    left: filmIcon.right
                    leftMargin: Theme.sourceRowIconGap
                    right: rowActions.left
                    rightMargin: Theme.gap
                    verticalCenter: parent.verticalCenter
                }
                text: {
                    var count = workspace.clipCountForSourceVideo(videoItem.sourceId)
                    return count === 0
                        ? "Video ohne Clips entfernen?"
                        : "Wirklich entfernen? " + count
                          + (count === 1 ? " Clip" : " Clips")
                }
                elide: Text.ElideRight
                color: Theme.warning
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeRow
                font.weight: Theme.medium
            }

            Text {
                id: videoName
                visible: !videoItem.renaming && !videoItem.removeArmed
                anchors {
                    left: filmIcon.right
                    leftMargin: Theme.sourceRowIconGap
                    right: rowActions.left
                    rightMargin: Theme.gap
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

                // Above `videoArea` for this text's own bounds (see the
                // comment on `videoArea`), so it has to repeat the single
                // click as well as add the double click, or a click on the
                // name itself would stop selecting the video.
                MouseArea {
                    id: renameArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.IBeamCursor
                    onClicked: {
                        videoList.currentIndex = videoItem.index
                        workspace.selectSourceVideo(videoItem.model.sourceId)
                    }
                    onDoubleClicked: {
                        renameField.text = videoItem.model.name
                        videoItem.renaming = true
                        renameField.forceActiveFocus()
                        renameField.selectAll()
                    }
                }
            }

            TextInput {
                id: renameField
                visible: videoItem.renaming
                anchors {
                    left: videoName.left
                    right: videoName.right
                    top: videoName.top
                }
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeRow
                font.weight: Theme.medium
                selectByMouse: true

                function commit() {
                    if (!videoItem.renaming)
                        return
                    videoItem.renaming = false
                    var trimmed = renameField.text.trim()
                    if (trimmed.length > 0 && trimmed !== videoItem.model.name)
                        workspace.renameSourceVideo(videoItem.sourceId, trimmed)
                    // The field is about to go invisible; leaving active
                    // focus on an invisible item is what left the Videos
                    // tab's own arrow-key navigation silently dead.
                    videoList.forceActiveFocus()
                }

                function cancel() {
                    videoItem.renaming = false
                    videoList.forceActiveFocus()
                }

                onAccepted: renameField.commit()
                onEditingFinished: renameField.commit()
                Keys.onEscapePressed: renameField.cancel()
            }

            Row {
                visible: !videoItem.removeArmed
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

                Text {
                    visible: !videoItem.model.available
                    text: "·  Nicht verfügbar"
                    color: Theme.warning
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Theme.medium
                }
            }

            // Reorder and remove: shown on hover so the resting row reads as
            // plainly as the Clip list, and armed rather than a modal
            // confirmation for removal, which no drawn-primitive component
            // in this visual system yet has to offer. Declared after
            // `videoArea` so its buttons sit above that full-row MouseArea
            // and actually receive the click.
            Row {
                id: rowActions
                anchors { right: parent.right; rightMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
                spacing: 0
                visible: videoArea.containsMouse || videoItem.removeArmed
                         || !videoItem.model.available

                // Always offered while unavailable, not just on hover: an
                // analyst scanning the Videos tab for what needs attention
                // should not have to hover every row to find the control.
                IconButton {
                    iconName: "rotate-cw"
                    tooltip: "Ersatzmedia auswählen"
                    visible: !videoItem.model.available
                    onClicked: workspace.relinkSourceVideo(videoItem.sourceId)
                }

                IconButton {
                    // No "chevron-up" is vendored in assets/icons/lucide/ —
                    // only chevron-down and chevron-right — so the up arrow
                    // is the down chevron rotated rather than a second icon.
                    iconName: "chevron-down"
                    rotation: 180
                    tooltip: "Nach oben verschieben"
                    enabled: videoItem.index > 0
                    onClicked: workspace.moveSourceVideoEarlier(videoItem.sourceId)
                }

                IconButton {
                    iconName: "chevron-down"
                    tooltip: "Nach unten verschieben"
                    enabled: videoItem.index < videoList.count - 1
                    onClicked: workspace.moveSourceVideoLater(videoItem.sourceId)
                }

                IconButton {
                    id: removeButton
                    iconName: "trash-2"
                    // The Clip count itself is `removeWarning`, in the row
                    // rather than here: a tooltip needs hover dwell the
                    // click-then-click confirmation never provides.
                    tooltip: videoItem.removeArmed ? "Entfernen bestätigen"
                                                   : "Video entfernen"
                    iconColor: videoItem.removeArmed ? Theme.warning : Theme.textMuted
                    onClicked: {
                        if (videoItem.removeArmed) {
                            disarmTimer.stop()
                            videoItem.removeArmed = false
                            workspace.removeSourceVideo(videoItem.sourceId)
                        } else {
                            videoItem.removeArmed = true
                            disarmTimer.restart()
                        }
                    }
                }
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
