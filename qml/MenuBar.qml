import QtQuick
import "."

/*
  The menu bar Windows and Linux draw inside the window.

  A `QMenuBar` is a Qt Widgets object and cannot live in a `QQuickWindow`. On
  macOS that does not matter — a parentless one becomes the *system* menu bar,
  which is platform behaviour ADR 0007 keeps — but everywhere else the menu bar
  belongs inside the window, and there is nowhere for a widget to go. So the
  same commands are drawn here, from the same primitives as every other
  surface: no Qt Quick Controls, and therefore no platform style underneath
  the design arguing with it.

  The entries are not this component's idea of what a menu bar contains. They
  arrive as data from `menu_bar.MENUS` by way of the view model, which is what
  makes it impossible for this bar and the macOS one to carry different
  commands.

  Nothing here declares a key sequence. The entry shows the sequence the
  platform uses, and the window listens for it exactly once — see the shortcuts
  at the bottom of `Main.qml`, which are disabled on macOS because the system
  menu bar is listening there instead.
*/
Item {
    id: root

    /* The bar, as `menu_bar.menu_model()` writes it down. */
    property var menus: []

    /* Which menu is open, if any, and where its title sits in the bar. */
    property int openIndex: -1
    property real openX: 0
    readonly property bool opened: openIndex >= 0

    signal commandRequested(string command)

    implicitHeight: Theme.menuBarHeight
    z: Theme.menuLayer

    function openMenu(index, x) {
        root.openIndex = index
        root.openX = x
    }

    function closeMenu() {
        root.openIndex = -1
    }

    function choose(command) {
        root.closeMenu()
        root.commandRequested(command)
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.app
    }

    // A press anywhere else in the window closes the open menu. It is
    // declared first so that the titles and the open menu are above it and
    // get their own presses; it exists at all only while a menu is open.
    MouseArea {
        id: elsewhere
        visible: root.opened
        x: -root.x
        y: -root.y
        width: root.parent ? root.parent.width : 0
        height: root.parent ? root.parent.height : 0
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPressed: root.closeMenu()
    }

    Row {
        id: titles
        anchors.left: parent.left
        anchors.leftMargin: Theme.gutter - Theme.menuTitlePadding
        height: parent.height

        Repeater {
            model: root.menus

            delegate: Item {
                id: title

                objectName: "menuTitle:" + title.modelData.title

                required property int index
                required property var modelData

                readonly property bool isOpen: root.openIndex === title.index

                width: caption.implicitWidth + 2 * Theme.menuTitlePadding
                height: titles.height

                Rectangle {
                    anchors.fill: parent
                    anchors.topMargin: Theme.menuTitleInset
                    anchors.bottomMargin: Theme.menuTitleInset
                    radius: Theme.radius
                    color: title.isOpen || pointer.containsMouse ? Theme.controlHover
                                                                 : Theme.transparent
                }

                Text {
                    id: caption
                    anchors.centerIn: parent
                    text: title.modelData.title
                    color: title.isOpen ? Theme.text : Theme.textMuted
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Theme.medium
                }

                MouseArea {
                    id: pointer
                    anchors.fill: parent
                    hoverEnabled: true
                    onPressed: {
                        if (title.isOpen) root.closeMenu()
                        else root.openMenu(title.index, titles.x + title.x)
                    }
                    // With one menu open, moving across the bar opens the next
                    // one, the way a menu bar has always behaved.
                    onContainsMouseChanged: {
                        if (containsMouse && root.opened)
                            root.openMenu(title.index, titles.x + title.x)
                    }
                }
            }
        }
    }

    // The open menu. One panel, refilled from whichever menu is open, because
    // only one of them can be.
    Rectangle {
        id: panel
        objectName: "openMenu"

        visible: root.opened
        x: root.openX
        y: root.height
        width: Math.max(Theme.menuMinimumWidth, entries.width)
        height: entries.height + 2 * Theme.menuPadding
        color: Theme.panel
        radius: Theme.radius
        border.width: Theme.border
        border.color: Theme.rule

        Column {
            id: entries
            y: Theme.menuPadding

            Repeater {
                model: root.opened ? root.menus[root.openIndex].entries : []

                delegate: Item {
                    id: entry

                    required property var modelData

                    readonly property bool isSeparator: modelData.separator

                    // The panel is as wide as its widest entry, so an entry
                    // states the width it needs and takes what it is given for
                    // the highlight. Binding it the other way round — the entry
                    // to the panel, the panel to the entries — is a loop.
                    implicitWidth: entry.isSeparator
                        ? 0
                        : label.implicitWidth + Theme.menuShortcutGap
                          + sequence.implicitWidth + 2 * Theme.menuItemPadding
                    height: entry.isSeparator ? Theme.menuSeparatorHeight
                                              : Theme.menuItemHeight

                    Rectangle {
                        visible: !entry.isSeparator && hover.containsMouse
                        width: panel.width
                        height: entry.height
                        color: Theme.controlHover
                    }

                    Rectangle {
                        visible: entry.isSeparator
                        anchors.verticalCenter: parent.verticalCenter
                        x: Theme.menuItemPadding
                        width: panel.width - 2 * Theme.menuItemPadding
                        height: Theme.border
                        color: Theme.rule
                    }

                    Text {
                        id: label
                        visible: !entry.isSeparator
                        anchors.verticalCenter: parent.verticalCenter
                        x: Theme.menuItemPadding
                        text: entry.isSeparator ? "" : entry.modelData.text
                        color: Theme.text
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Theme.regular
                    }

                    Text {
                        id: sequence
                        visible: !entry.isSeparator
                        anchors.verticalCenter: parent.verticalCenter
                        x: panel.width - Theme.menuItemPadding - width
                        text: entry.isSeparator ? "" : entry.modelData.shortcut
                        color: Theme.textFaint
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeLabel
                        font.weight: Theme.regular
                    }

                    MouseArea {
                        id: hover
                        objectName: entry.isSeparator ? "" : "menuEntry:" + entry.modelData.command
                        visible: !entry.isSeparator
                        width: panel.width
                        height: entry.height
                        hoverEnabled: true
                        onClicked: root.choose(entry.modelData.command)
                    }
                }
            }
        }
    }

    // Escape leaves the menu rather than the state the window is in. The
    // window's own Escape is disabled while a menu is open, so the sequence is
    // never declared twice at once.
    Shortcut {
        sequence: "Escape"
        enabled: root.opened
        onActivated: root.closeMenu()
    }
}
