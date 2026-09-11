import QtQuick
import "."

/*
  A working toolbar, not a wordmark strip.

  The 'VIDEO ANALYSE' strip beneath the native menu bar is deleted (ADR 0007):
  a single-window desktop tool does not announce its own name in its chrome.
  What sits here instead are the actions and the Analysis this window is about.
*/
Rectangle {
    id: root


    implicitHeight: Theme.toolbarHeight
    color: Theme.app

    Row {
        id: fileActions
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.gutter - 4
        spacing: 2

        IconButton { iconName: "file-plus";   tooltip: "Neue Analyse" }
        IconButton { iconName: "folder-open"; tooltip: "Analyse öffnen" }
        IconButton { iconName: "save";        tooltip: "Analyse speichern" }
    }

    Rectangle {
        id: separator
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: fileActions.right
        anchors.leftMargin: Theme.gap
        width: Theme.border
        height: 18
        color: Theme.rule
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: separator.right
        anchors.leftMargin: Theme.gap - 2
        spacing: 2

        IconButton { iconName: "film-plus"; tooltip: "Video hinzufügen" }
        IconButton { iconName: "upload";    tooltip: "Zusammenschnitt exportieren" }
    }

    // The Analysis name and its unsaved state.
    Row {
        anchors.centerIn: parent
        spacing: Theme.gap

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: workspace.analysisTitle
            color: Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeTitle
            font.weight: Theme.medium
        }

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            visible: workspace.dirty
            width: 6
            height: 6
            radius: 3
            color: Theme.textMuted

            Tip { target: dirtyArea; text: "Nicht gespeicherte Änderungen" }
            MouseArea { id: dirtyArea; anchors.fill: parent; anchors.margins: -5; hoverEnabled: true }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: Theme.gutter - 4
        spacing: 2

        IconButton {
            iconName: "panel-left"
            tooltip: "Seitenleiste ein-/ausblenden"
            active: workspace.sidebarVisible
            onClicked: workspace.toggleSidebar()
        }
        IconButton { iconName: "maximize"; tooltip: "Vollbild" }
    }

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: Theme.border
        color: Theme.rule
    }
}
