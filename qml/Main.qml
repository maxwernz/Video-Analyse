import QtQuick
import "."

/*
  The window, and the application's single QML entry point.

  This is the shell: the three surfaces, the one hairline, the vendored
  typography and a toolbar. The timeline, the transport, the Clip list and the
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

    // The Analysis this window is about arrives with the view model in #47.
    // Until then the shell shows what a freshly started application shows,
    // and a test pins this string to the workflow's own.
    property string analysisTitle: "Unbenannte Analyse"
    property bool dirty: false
    property bool sidebarVisible: true

    width: Theme.windowWidth
    height: Theme.windowHeight
    minimumWidth: Theme.windowMinimumWidth
    minimumHeight: Theme.windowMinimumHeight
    visible: true
    color: Theme.app
    title: "Video Analyse"

    Toolbar {
        id: toolbar
        anchors { top: parent.top; left: parent.left; right: parent.right }

        analysisTitle: window.analysisTitle
        dirty: window.dirty
        sidebarVisible: window.sidebarVisible
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
            anchors.fill: parent
        }
    }
}
