import QtQuick
import "."

/*
  The window.

  Three states of one shell: `empty`, `workspace` and `editing`. The Clip
  editor takes its 360px from the shell, which is why the video comes back to
  full size on leaving the editing state without anything having to remember
  its old geometry.

  The menu bar is not here. It is a real QMenuBar created in Python, so on
  macOS it is the system menu bar: ADR 0007 keeps platform *behaviour* while
  owning the appearance, and a menu drawn inside the window would be the
  wrong side of that line.
*/
Window {
    id: window

    width: 1440
    height: 900
    minimumWidth: 1200
    minimumHeight: 760
    visible: true
    color: Theme.app
    title: workspace.windowTitle

    readonly property bool editing: workspace.mode === "editing"
    readonly property bool empty: workspace.mode === "empty"

    Toolbar {
        id: toolbar
        anchors { top: parent.top; left: parent.left; right: parent.right }
    }

    // --- Sidebar ----------------------------------------------------------

    Sidebar {
        id: sidebar
        anchors { top: toolbar.bottom; left: parent.left; bottom: parent.bottom }
        width: workspace.sidebarVisible ? sidebarWidth : 0
        visible: width > 0

        property int sidebarWidth: Theme.sidebarWidth

        Behavior on width {
            enabled: !splitter.pressed
            NumberAnimation { duration: 130; easing.type: Easing.OutCubic }
        }
    }

    MouseArea {
        id: splitter
        visible: workspace.sidebarVisible
        anchors { top: toolbar.bottom; bottom: parent.bottom }
        x: sidebar.width - 2
        width: 5
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
            right: editor.visible ? editor.left : parent.right
            bottom: parent.bottom
        }

        Stage {
            id: stage
            anchors { top: parent.top; left: parent.left; right: parent.right; bottom: timeline.top }
            visible: !window.empty
            stillSource: captureStill
        }

        EmptyStage {
            anchors { top: parent.top; left: parent.left; right: parent.right; bottom: timeline.top }
            visible: window.empty
        }

        Timeline {
            id: timeline
            // Named so verify.py can find it and send real mouse events at it.
            objectName: "timeline"
            anchors { left: parent.left; right: parent.right; bottom: transport.top }
            height: Theme.timelineHeight
        }

        Transport {
            id: transport
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        }
    }

    // --- Clip editor ------------------------------------------------------

    ClipEditor {
        id: editor
        anchors { top: toolbar.bottom; right: parent.right; bottom: parent.bottom }
        width: Theme.editorWidth
        visible: window.editing
    }

    // --- Shortcuts: platform behaviour, kept ------------------------------

    Shortcut { sequence: "Space";       onActivated: workspace.playPause() }
    Shortcut { sequence: "Left";        onActivated: workspace.stepBackward() }
    Shortcut { sequence: "Right";       onActivated: workspace.stepForward() }
    Shortcut { sequence: "Shift+Left";  onActivated: workspace.jumpBackward() }
    Shortcut { sequence: "Shift+Right"; onActivated: workspace.jumpForward() }
    Shortcut { sequence: "M";           onActivated: workspace.markBoundary() }
    Shortcut {
        sequence: "Escape"
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
}
