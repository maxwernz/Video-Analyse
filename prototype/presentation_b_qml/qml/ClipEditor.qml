import QtQuick
import "."

/*
  The dedicated Clip-editing state: a structured form, 360px wide, beside a
  large paused frame.

  It replaces both the centered modal and the permanent bottom dock. Sections
  are separated by rules rather than by boxes, because an elevated card is the
  thing ADR 0007 took away.
*/
Rectangle {
    id: root


    implicitWidth: Theme.editorWidth
    color: Theme.panel

    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Theme.border
        color: Theme.rule
    }

    // Header
    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.leftMargin: Theme.gutter
        anchors.rightMargin: Theme.gutter - 4
        height: Theme.toolbarHeight

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: workspace.draftIsNew ? "Neuer Clip" : "Clip bearbeiten"
            color: Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeTitle
            font.weight: Theme.medium
        }

        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            iconName: "x"
            tooltip: "Abbrechen"
            onClicked: workspace.cancelDraft()
        }
    }

    Rectangle {
        id: headerRule
        anchors { top: header.bottom; left: parent.left; right: parent.right }
        anchors.leftMargin: Theme.border
        height: Theme.border
        color: Theme.rule
    }

    Flickable {
        id: form
        anchors { top: headerRule.bottom; left: parent.left; right: parent.right; bottom: actionsRule.top }
        anchors.leftMargin: Theme.border
        clip: true
        contentHeight: sections.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: sections
            width: form.width

            // Title
            Section {
                width: parent.width
                label: "Titel"

                Field {
                    width: parent.width
                    text: workspace.draftName
                    placeholder: "Clip benennen"
                    onEdited: function (value) { workspace.setDraftName(value) }
                }
            }

            // Category
            Section {
                width: parent.width
                label: "Kategorie"

                Flow {
                    width: parent.width
                    spacing: 6

                    Repeater {
                        model: categoryModel

                        Item {
                            required property var model
                            width: chipRow.implicitWidth + 20
                            height: 26

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radius
                                color: model.selected ? Theme.selection
                                                      : (chipArea.containsMouse ? Theme.controlHover : Theme.control)
                                border.width: Theme.border
                                border.color: model.selected ? Theme.accent : Theme.controlBorder
                            }

                            Row {
                                id: chipRow
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 7; height: 7; radius: 3.5
                                    color: model.color
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: model.name
                                    color: model.selected ? Theme.text : Theme.textMuted
                                    font.family: Theme.uiFamily
                                    font.pixelSize: Theme.sizeBody
                                    font.weight: model.selected ? Theme.medium : Theme.regular
                                }
                            }

                            MouseArea {
                                id: chipArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: workspace.setDraftCategory(
                                               model.selected ? "" : model.categoryId)
                            }
                        }
                    }
                }
            }

            // Boundaries
            Section {
                width: parent.width
                label: "Grenzen"

                Row {
                    width: parent.width
                    spacing: Theme.gap + 2

                    TimecodeField {
                        width: (parent.width - Theme.gap - 2) / 2
                        label: "Start"
                        which: "start"
                        value: workspace.draftStartText
                    }

                    TimecodeField {
                        width: (parent.width - Theme.gap - 2) / 2
                        label: "Ende"
                        which: "end"
                        value: workspace.draftEndText
                    }
                }

                // The live duration readout: the number being edited, in the
                // form the Clip list will show it.
                Row {
                    width: parent.width
                    spacing: Theme.gap

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Dauer"
                        color: Theme.textMuted
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeLabel
                        font.weight: Theme.medium
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: workspace.draftDurationText
                        color: Theme.text
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeTimecode
                        font.weight: Theme.medium
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "· bewegt das Video mit"
                        color: Theme.textFaint
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeLabel
                        font.weight: Theme.regular
                    }
                }
            }

            // Notes
            Section {
                width: parent.width
                label: "Notizen"
                lastSection: true

                Rectangle {
                    width: parent.width
                    height: 108
                    radius: Theme.radius
                    color: Theme.control
                    border.width: Theme.border
                    border.color: notes.activeFocus ? Theme.accent : Theme.controlBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: Theme.gap + 2
                        clip: true
                        contentHeight: notes.contentHeight

                        TextEdit {
                            id: notes
                            width: parent.width
                            text: workspace.draftNotes
                            wrapMode: TextEdit.Wrap
                            color: Theme.text
                            selectionColor: Theme.accent
                            selectedTextColor: Theme.accentOn
                            font.family: Theme.uiFamily
                            font.pixelSize: Theme.sizeBody
                            font.weight: Theme.regular
                            onEditingFinished: workspace.setDraftNotes(text)

                            Text {
                                anchors.fill: parent
                                visible: notes.text === "" && !notes.activeFocus
                                text: "Was ist hier passiert?"
                                color: Theme.textFaint
                                font: notes.font
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: actionsRule
        anchors { bottom: actions.top; left: parent.left; right: parent.right }
        anchors.leftMargin: Theme.border
        height: Theme.border
        color: Theme.rule
    }

    // One accent primary and one quiet secondary.
    Item {
        id: actions
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: 64

        Text {
            anchors { left: parent.left; leftMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
            anchors.right: buttons.left
            anchors.rightMargin: Theme.gap
            visible: workspace.draftError !== ""
            text: workspace.draftError
            elide: Text.ElideRight
            color: "#DE8241"
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeLabel
            font.weight: Theme.regular
        }

        Row {
            id: buttons
            anchors { right: parent.right; rightMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
            spacing: Theme.gap

            TextButton {
                label: "Abbrechen"
                onClicked: workspace.cancelDraft()
            }

            TextButton {
                primary: true
                label: workspace.draftIsNew ? "Clip anlegen" : "Übernehmen"
                enabled: workspace.draftValid
                onClicked: workspace.commitDraft()
            }
        }
    }
}
