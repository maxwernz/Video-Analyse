import QtQuick
import "."

/*
  The left sidebar: a segmented control over two lists.

  There is no column header. A spreadsheet header strip is not something a
  coach reads, and in the captured evidence it was what truncated the
  Source-video column at the default sidebar width.
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
            segmentWidth: Math.floor((parent.width - 2) / 2)
            currentIndex: workspace.sidebarTab === "clips" ? 0 : 1
            onSelected: function (index) {
                workspace.setSidebarTab(index === 0 ? "clips" : "videos")
            }
        }
    }

    Rectangle {
        id: tabsRule
        anchors { top: tabs.bottom; topMargin: Theme.gutter - 4; left: parent.left; right: parent.right }
        height: Theme.border
        color: Theme.rule
    }

    // Clips
    ListView {
        id: clipList
        anchors { top: tabsRule.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: workspace.sidebarTab === "clips"
        clip: true
        model: clipModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollHint { flickable: clipList }

        // One delegate, two shapes. A Loader would recycle its item out from
        // under these bindings and spend the first frame reading a null model.
        delegate: Item {
            id: rowItem
            required property var model
            required property int index

            width: clipList.width
            height: model.kind === "category" ? 30 : Theme.clipRowHeight

            // --- Category header ---
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
                    anchors.verticalCenterOffset: 1
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.gutter
                    width: 6
                    height: 6
                    radius: 3
                    color: rowItem.model.categoryColor
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
                           : (rowArea.containsMouse ? Qt.rgba(1, 1, 1, 0.025) : "transparent")
                }

                // 3px full-colour Category bar at the leading edge.
                Rectangle {
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                    width: 3
                    color: rowItem.model.categoryColor
                }

                Text {
                    id: title
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.right: badge.visible ? badge.left : times.left
                    anchors.rightMargin: 6
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
                    anchors.rightMargin: 8
                    width: badgeText.implicitWidth + 9
                    height: 16
                    radius: 2
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

                // Start and duration, right-aligned, tabular.
                Row {
                    id: times
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.gutter
                    spacing: 10

                    Text {
                        text: rowItem.model.startText
                        color: Theme.text
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeTimecode
                        font.weight: Theme.medium
                    }

                    Text {
                        width: 38
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
                    // Selecting a Clip activates its Source video and seeks to its start.
                    onClicked: workspace.navigateToClip(rowItem.model.clipId)
                    onDoubleClicked: workspace.editClip(rowItem.model.clipId)
                }

                Tip { target: rowArea; text: rowItem.model.sourceCue }
            }
        }
    }

    // Videos
    ListView {
        id: videoList
        anchors { top: tabsRule.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: workspace.sidebarTab === "videos"
        clip: true
        model: sourceModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollHint { flickable: videoList }

        delegate: Item {
            id: videoItem
            required property var model
            width: videoList.width
            height: 52

            Rectangle {
                anchors.fill: parent
                color: videoItem.model.active ? Theme.selection
                                              : (videoArea.containsMouse ? Qt.rgba(1, 1, 1, 0.025) : "transparent")
            }

            // The Active Source video is a selection: the accent may say so.
            Rectangle {
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: 3
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
                source: Theme.icon(videoItem.model.missing ? "alert" : "film",
                                   videoItem.model.missing ? "#DE8241"
                                                           : (videoItem.model.active ? Theme.text : Theme.textMuted))
            }

            Text {
                id: videoName
                anchors { left: filmIcon.right; leftMargin: 10; right: parent.right; rightMargin: Theme.gutter }
                anchors.top: parent.top
                anchors.topMargin: 9
                text: videoItem.model.name
                elide: Text.ElideMiddle
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeRow
                font.weight: Theme.medium
            }

            Text {
                anchors { left: videoName.left; top: videoName.bottom; topMargin: 3 }
                text: videoItem.model.durationText + "   ·   " + videoItem.model.clipCount + " Clips"
                       + (videoItem.model.missing ? "   ·   Datei fehlt" : "")
                color: videoItem.model.missing ? "#DE8241" : Theme.textFaint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.sizeRuler
                font.weight: Theme.regular
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
