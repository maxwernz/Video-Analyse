import QtQuick
import "."

/*
  The window, and the application's single QML entry point.

  This is the shell: the three surfaces, the one hairline, the vendored
  typography, a toolbar and the transport. The timeline, the Clip list and the
  Clip editor arrive with the tickets that own them, each taking its place in
  the geometry already laid out here.

  The Clip editor will take its 360px from the shell rather than from the
  video, which is why the video comes back to full size on leaving the editing
  state without anything having to remember its old geometry.

  The menu bar is not here. It is a real QMenuBar created in Python, so on
  macOS it is the system menu bar: ADR 0007 keeps platform *behaviour* while
  owning the appearance, and a menu drawn inside the window would be the
  wrong side of that line.
*/
Window {
    id: window

    property bool sidebarVisible: true

    width: Theme.windowWidth
    height: Theme.windowHeight
    minimumWidth: Theme.windowMinimumWidth
    minimumHeight: Theme.windowMinimumHeight
    visible: true
    color: Theme.app

    // The Analysis, and whether it is safe to close. Both are the workflow's
    // own words: the marker, the em dash and the application name are decided
    // in Python, so the title bar and the toolbar cannot spell them apart.
    title: workspace.windowTitle

    // Every way out of the window — the menu entry, the red button, the
    // platform's own quit — arrives here, so the unsaved-changes question is
    // asked once and in one place.
    onClosing: function (close) { close.accepted = workspace.requestClose() }

    Toolbar {
        id: toolbar
        objectName: "toolbar"
        anchors { top: parent.top; left: parent.left; right: parent.right }

        analysisTitle: workspace.analysisTitle
        dirty: workspace.dirty
        sidebarVisible: window.sidebarVisible
        onNewAnalysisRequested: workspace.newAnalysis()
        onOpenAnalysisRequested: workspace.openAnalysis()
        onSaveAnalysisRequested: workspace.saveAnalysis()
        onSidebarToggleRequested: window.sidebarVisible = !window.sidebarVisible
    }

    // --- Sidebar ----------------------------------------------------------

    Sidebar {
        id: sidebar
        anchors { top: toolbar.bottom; left: parent.left; bottom: parent.bottom }
        width: window.sidebarVisible ? sidebarWidth : 0
        visible: width > 0

        property int sidebarWidth: Theme.sidebarWidth

        Behavior on width {
            enabled: !splitter.pressed
            NumberAnimation { duration: Theme.paneAnimationMs; easing.type: Easing.OutCubic }
        }
    }

    MouseArea {
        id: splitter
        visible: window.sidebarVisible
        anchors { top: toolbar.bottom; bottom: parent.bottom }
        x: sidebar.width - Math.floor(Theme.splitterWidth / 2)
        width: Theme.splitterWidth
        cursorShape: Qt.SizeHorCursor
        property real pressX: 0
        property int pressWidth: 0
        onPressed: function (mouse) { pressX = mouse.x; pressWidth = sidebar.sidebarWidth }
        onPositionChanged: function (mouse) {
            if (!pressed) return
            sidebar.sidebarWidth = Math.max(Theme.sidebarMinimum,
                                   Math.min(Theme.sidebarMaximum,
                                            pressWidth + (mouse.x - pressX)))
        }
    }

    // --- Video area -------------------------------------------------------

    Item {
        id: main
        anchors {
            top: toolbar.bottom
            left: sidebar.right
            right: parent.right
            bottom: parent.bottom
        }

        Stage {
            id: stage
            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                bottom: timeline.top
            }
        }

        // The workspace's only seek surface (ADR 0006).
        Timeline {
            id: timeline
            anchors { left: parent.left; right: parent.right; bottom: transport.top }
            height: Theme.timelineHeight
        }

        Transport {
            id: transport
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        }
    }

    // --- Shortcuts: platform behaviour, kept ------------------------------
    //
    // The transport's own keys.

    Shortcut { sequence: "Space";       onActivated: workspace.playPause() }
    Shortcut { sequence: "Left";        onActivated: workspace.stepBackward() }
    Shortcut { sequence: "Right";       onActivated: workspace.stepForward() }
    Shortcut { sequence: "Shift+Left";  onActivated: workspace.jumpBackward() }
    Shortcut { sequence: "Shift+Right"; onActivated: workspace.jumpForward() }

    // The document commands' keys, everywhere the menu bar is not carrying
    // them. On macOS the menu bar is the *system* menu bar, Cocoa answers its
    // key equivalents before the window ever sees them, and a second listener
    // here would only make the sequence ambiguous. Everywhere else the
    // parentless menu bar is not attached to this Qt Quick window, so the
    // window listens for itself. The sequences are the platform's own either
    // way: `StandardKey` names the command, not the keys.

    readonly property bool menuBarOwnsTheKeys: Qt.platform.os === "osx"

    Shortcut {
        sequences: [StandardKey.New]
        enabled: !window.menuBarOwnsTheKeys
        onActivated: workspace.newAnalysis()
    }
    Shortcut {
        sequences: [StandardKey.Open]
        enabled: !window.menuBarOwnsTheKeys
        onActivated: workspace.openAnalysis()
    }
    Shortcut {
        sequences: [StandardKey.Save]
        enabled: !window.menuBarOwnsTheKeys
        onActivated: workspace.saveAnalysis()
    }
    Shortcut {
        sequences: [StandardKey.SaveAs]
        enabled: !window.menuBarOwnsTheKeys
        onActivated: workspace.saveAnalysisAs()
    }
    Shortcut {
        sequences: [StandardKey.Close]
        enabled: !window.menuBarOwnsTheKeys
        onActivated: window.close()
    }
}
