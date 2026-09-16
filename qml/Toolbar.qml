import QtQuick
import "."

/*
  A working toolbar, not a wordmark strip.

  The 'VIDEO ANALYSE' strip beneath the native menu bar is deleted (ADR 0007):
  a single-window desktop tool does not announce its own name in its chrome.
  What sits here instead are the actions and the Analysis this window is about.

  The actions are a shell. Each one carries the signal the workflow will be
  connected to, and connecting them is #47's work; the Analysis this toolbar
  describes arrives with it. Until then the data comes in as properties, so
  the component can be loaded and inspected on its own.
*/
Rectangle {
    id: root

    property string analysisTitle
    property bool dirty: false
    property bool sidebarVisible: true

    signal newAnalysisRequested()
    signal openAnalysisRequested()
    signal saveAnalysisRequested()
    signal addVideoRequested()
    signal exportRequested()
    signal categoriesRequested()
    signal sidebarToggleRequested()
    signal fullscreenRequested()

    implicitHeight: Theme.toolbarHeight
    color: Theme.app

    Row {
        id: fileActions
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.gutter - Theme.unit
        spacing: Theme.toolbarActionSpacing

        IconButton {
            iconName: "file-plus"
            tooltip: "Neue Analyse"
            onClicked: root.newAnalysisRequested()
        }
        IconButton {
            iconName: "folder-open"
            tooltip: "Analyse öffnen"
            onClicked: root.openAnalysisRequested()
        }
        IconButton {
            iconName: "save"
            tooltip: "Analyse speichern"
            onClicked: root.saveAnalysisRequested()
        }
    }

    Rectangle {
        id: separator
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: fileActions.right
        anchors.leftMargin: Theme.gap
        width: Theme.border
        height: Theme.toolbarSeparatorHeight
        color: Theme.rule
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: separator.right
        anchors.leftMargin: Theme.gap - Theme.toolbarActionSpacing
        spacing: Theme.toolbarActionSpacing

        IconButton {
            iconName: "file-video"
            tooltip: "Video hinzufügen"
            onClicked: root.addVideoRequested()
        }
        IconButton {
            iconName: "upload"
            tooltip: "Zusammenschnitt exportieren"
            onClicked: root.exportRequested()
        }
        IconButton {
            iconName: "circle-dot"
            tooltip: "Kategorien verwalten"
            onClicked: root.categoriesRequested()
        }
    }

    // The Analysis name and its unsaved state.
    Row {
        anchors.centerIn: parent
        spacing: Theme.gap

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.analysisTitle
            color: Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeTitle
            font.weight: Theme.medium
        }

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.dirty
            width: Theme.dirtyMarkerSize
            height: Theme.dirtyMarkerSize
            radius: Theme.dirtyMarkerSize / 2
            color: Theme.textMuted

            Tip { target: dirtyArea; text: "Nicht gespeicherte Änderungen" }
            MouseArea {
                id: dirtyArea
                anchors.fill: parent
                anchors.margins: -Theme.unit
                hoverEnabled: true
            }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: Theme.gutter - Theme.unit
        spacing: Theme.toolbarActionSpacing

        IconButton {
            iconName: "panel-left"
            tooltip: "Seitenleiste ein-/ausblenden"
            active: root.sidebarVisible
            onClicked: root.sidebarToggleRequested()
        }
        IconButton {
            iconName: "maximize"
            tooltip: "Vollbild"
            onClicked: root.fullscreenRequested()
        }
    }

    // The one hairline.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: Theme.border
        color: Theme.rule
    }
}
