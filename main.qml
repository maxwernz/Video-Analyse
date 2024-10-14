import QtQuick 2.15
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

ApplicationWindow {
    visible: true
    width: 1600
    height: 900
    title: "Modern Video Player"

    // Main layout for the window
    ColumnLayout {
        anchors.fill: parent

        // Top control bar with File Menu
        MenuBar {
            Menu {
                title: "File"
                Action { text: "Load Video"; onTriggered: console.log("Load Video") }
                Action { text: "Load Analysis"; onTriggered: console.log("Load Analysis") }
                Action { text: "Save Analysis"; onTriggered: console.log("Save Analysis") }
                Action { text: "Export Clips"; onTriggered: console.log("Export Clips") }
            }
        }

        // Main content area with video and clip list
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Left: TableView for clips (replaces TreeView)
            TableView {
                Layout.fillHeight: true
                model: ListModel {
                    ListElement { clip: "Clip 1"; start: "00:00"; stop: "00:10" }
                    ListElement { clip: "Clip 2"; start: "00:15"; stop: "00:30" }
                }
                TableViewColumn { role: "clip"; title: "Clip" }
                TableViewColumn { role: "start"; title: "Start" }
                TableViewColumn { role: "stop"; title: "Stop" }
                headerVisible: true
            }

            // Right: Video Widget
            Item {
                Layout.fillHeight: true
                Layout.fillWidth: true
                Rectangle {
                    color: "black"
                    anchors.fill: parent

                    // Simulate video player area
                    Text {
                        text: "Video Player"
                        color: "white"
                        anchors.centerIn: parent
                        font.pixelSize: 24
                    }
                }
            }
        }

        // Control bar at the bottom
        Rectangle {
            height: 80
            width: parent.width
            color: "#2e2e2e"
            anchors.horizontalCenter: parent.horizontalCenter

            RowLayout {
                anchors.fill: parent
                spacing: 20
                padding: 10

                // Mute/Unmute button
                Button {
                    icon.source: playPauseButton.checked ? "icons/sound.svg" : "icons/mute.svg"
                    checkable: true
                    tooltip: playPauseButton.checked ? "Mute" : "Unmute"
                }

                // Backward button
                Button {
                    icon.source: "icons/backward.svg"
                    tooltip: "Rewind"
                }

                // Play/Pause button
                Button {
                    icon.source: playPauseButton.checked ? "icons/pause.svg" : "icons/play.svg"
                    checkable: true
                    checked: false
                    tooltip: checked ? "Pause" : "Play"
                }

                // Forward button
                Button {
                    icon.source: "icons/forward.svg"
                    tooltip: "Fast Forward"
                }

                // Speed control (ComboBox)
                ComboBox {
                    id: speedBox
                    Layout.fillWidth: true
                    model: ["0.25x", "0.5x", "1x", "2x"]
                    currentIndex: 2
                    tooltip: "Playback Speed"
                }

                // Record Clip button
                Button {
                    text: "Clip"
                    icon.source: clipButton.checked ? "icons/record_action.svg" : "icons/record.svg"
                    checkable: true
                    tooltip: "Record Clip"
                }
            }
        }
    }
}