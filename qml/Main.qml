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

  The menu bar is in two places, because a menu bar is in two places. On macOS
  it is a real parentless QMenuBar created in Python — the *system* menu bar,
  which is platform behaviour ADR 0007 keeps. Windows and Linux put the menu
  bar inside the window, where a widget cannot go, so there the same commands
  are drawn by `MenuBar.qml` from the same definition. `nativeMenuBar` is the
  one place that decides which, and the window's document shortcuts read it
  too, so the sequences are listened for once rather than ambiguously twice.
*/
Window {
    id: window

    property bool sidebarVisible: true

    // Whether this platform's menu bar lives outside the window. macOS's does,
    // and Python has already made it; everywhere else this window draws its
    // own. Both the menu bar below and the document shortcuts at the bottom of
    // this file read this one property, so a platform cannot end up with two
    // menu bars or with none.
    property bool nativeMenuBar: Qt.platform.os === "osx"

    // Key events arrive at the Python filter installed on this Window. Unlike
    // the QML `Keys` attached property, that filter continues to see document
    // sequences while a field has focus; unlike individual `Shortcut` items,
    // it reads the shared command definition rather than a second key list.
    Component.onCompleted: workspace.installMenuShortcutHandler(window)

    // The Clip-editing state, which is a state of the shell rather than of any
    // one surface: the editor takes its 360px out of the window, so the video
    // comes back to full size on the way out without anything remembering how
    // big it used to be.
    readonly property bool editing: workspace.editing

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

    // The in-window menu bar, and nothing at all where the system has one.
    MenuBar {
        id: menuBar
        objectName: "menuBar"
        anchors { top: parent.top; left: parent.left; right: parent.right }
        visible: !window.nativeMenuBar
        height: visible ? Theme.menuBarHeight : 0
        menus: workspace.menus
        onCommandRequested: function (command) { workspace.runMenuCommand(command) }
    }

    // Close is a request of the window, whichever menu bar asked: the red
    // button, the platform's quit and the menu entry all arrive at `onClosing`,
    // so the unsaved-changes question is asked once.
    Connections {
        target: workspace
        function onCloseRequested() { window.close() }
    }

    Toolbar {
        id: toolbar
        objectName: "toolbar"
        anchors { top: menuBar.bottom; left: parent.left; right: parent.right }

        analysisTitle: workspace.analysisTitle
        dirty: workspace.dirty
        sidebarVisible: window.sidebarVisible
        onNewAnalysisRequested: workspace.newAnalysis()
        onOpenAnalysisRequested: workspace.openAnalysis()
        onSaveAnalysisRequested: workspace.saveAnalysis()
        onAddVideoRequested: workspace.addSourceVideo()
        onCategoriesRequested: workspace.showCategoryManagement()
        onSidebarToggleRequested: window.sidebarVisible = !window.sidebarVisible
    }

    // --- Sidebar ----------------------------------------------------------

    Sidebar {
        id: sidebar
        objectName: "sidebar"
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
        objectName: "videoArea"
        anchors {
            top: toolbar.bottom
            left: sidebar.right
            right: editor.visible ? editor.left : parent.right
            bottom: parent.bottom
        }

        Stage {
            id: stage
            objectName: "videoStage"
            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                bottom: timeline.top
            }
            visible: workspace.hasVideo
        }

        EmptyStage {
            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                bottom: timeline.top
            }
            visible: !workspace.hasVideo
            containsDrag: windowDropArea.containsDrag
            onAddRequested: workspace.addSourceVideo()
        }

        // The workspace's only seek surface (ADR 0006).
        Timeline {
            id: timeline
            objectName: "timeline"
            anchors { left: parent.left; right: parent.right; bottom: transport.top }
            height: Theme.timelineHeight
        }

        Transport {
            id: transport
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        }
    }

    // Add Source videos anywhere on the window; the operation stays additive.
    DropArea {
        id: windowDropArea
        objectName: "windowDropArea"
        anchors.fill: parent
        z: Theme.dropLayer
        onDropped: function (drop) {
            workspace.addDroppedSourceVideos(drop.urls)
            drop.acceptProposedAction()
        }
    }

    // --- The Clip editor --------------------------------------------------

    ClipEditor {
        id: editor
        anchors { top: toolbar.bottom; right: parent.right; bottom: parent.bottom }
        width: Theme.editorWidth
        visible: window.editing
    }

    // --- Shortcuts: platform behaviour, kept ------------------------------
    //
    // The transport's own keys.

    Shortcut { sequence: "Space";       onActivated: workspace.playPause() }
    Shortcut { sequence: "Left";        onActivated: workspace.stepBackward() }
    Shortcut { sequence: "Right";       onActivated: workspace.stepForward() }
    Shortcut { sequence: "Shift+Left";  onActivated: workspace.jumpBackward() }
    Shortcut { sequence: "Shift+Right"; onActivated: workspace.jumpForward() }

    // Marking a Clip, and the two ways out of the state it opens. Escape
    // leaves whichever of them the window is in, because an analyst pressing
    // it means "not this" rather than "cancel the draft specifically".
    Shortcut { sequence: "M"; onActivated: workspace.markBoundary() }
    Shortcut {
        sequence: "Escape"
        // An open menu takes Escape first, and says so itself, so the sequence
        // is never declared twice at once.
        enabled: !menuBar.opened
        onActivated: {
            if (window.editing) workspace.cancelDraft()
            else workspace.cancelPending()
        }
    }
    Shortcut {
        sequence: "Return"
        enabled: window.editing
        onActivated: workspace.commitDraft()
    }

    Shortcut {
        sequence: Qt.platform.os === "osx" ? "Meta+Shift+V" : "Ctrl+Shift+V"
        onActivated: workspace.addSourceVideo()
    }
}
