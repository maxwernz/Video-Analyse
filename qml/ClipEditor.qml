import QtQuick
import "."

/*
  The dedicated Clip-editing state: a structured form, 360px wide, beside a
  large paused frame.

  It replaces both the centered modal and the permanent bottom dock. Sections
  are separated by rules rather than by boxes, because an elevated card is the
  thing ADR 0007 took away.

  One form serves both a newly marked Clip and an existing one, which is why
  nothing here asks which it is except the two words that name the state. The
  draft it edits lives in Python and never reaches the Analysis until the
  primary is pressed; cancelling is one path for both, because there is
  nothing to put back.
*/
Rectangle {
    id: root

    objectName: "clipEditor"
    implicitWidth: Theme.editorWidth
    color: Theme.panel

    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Theme.border
        color: Theme.rule
    }

    // --- Header -----------------------------------------------------------

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.leftMargin: Theme.gutter
        anchors.rightMargin: Theme.gutter - Theme.unit
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

    // --- The form ---------------------------------------------------------

    Flickable {
        id: form
        anchors {
            top: headerRule.bottom
            left: parent.left
            right: parent.right
            bottom: actionsRule.top
        }
        anchors.leftMargin: Theme.border
        clip: true
        contentHeight: sections.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: sections
            width: form.width

            Section {
                width: parent.width
                label: "Titel"

                Field {
                    objectName: "titleField"
                    width: parent.width
                    text: workspace.draftName
                    placeholder: "Clip benennen"
                    onEdited: function (value) { workspace.setDraftName(value) }
                }
            }

            Section {
                width: parent.width
                label: "Kategorie"

                Flow {
                    width: parent.width
                    spacing: Theme.chipSpacing

                    Repeater {
                        model: workspace.categoryModel

                        Item {
                            required property var model

                            objectName: "categoryChip"
                            width: chipRow.implicitWidth + Theme.chipPadding * 2
                            height: Theme.chipHeight

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radius
                                color: model.selected
                                       ? Theme.selection
                                       : (chipArea.containsMouse ? Theme.controlHover
                                                                 : Theme.control)
                                border.width: Theme.border
                                border.color: model.selected ? Theme.accent
                                                             : Theme.controlBorder
                            }

                            Row {
                                id: chipRow
                                anchors.centerIn: parent
                                spacing: Theme.chipSpacing

                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: Theme.chipDotSize
                                    height: Theme.chipDotSize
                                    radius: Theme.chipDotSize / 2
                                    color: model.color
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: model.name
                                    color: model.selected ? Theme.text : Theme.textMuted
                                    font.family: Theme.uiFamily
                                    font.pixelSize: Theme.sizeBody
                                    font.weight: model.selected ? Theme.medium
                                                                : Theme.regular
                                }
                            }

                            MouseArea {
                                id: chipArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                // Pressing the chosen Category again takes it
                                // off: a Clip may belong to no Category, and
                                // there is nowhere else to say so.
                                onClicked: workspace.setDraftCategory(
                                               model.selected ? "" : model.categoryId)
                            }
                        }
                    }
                }
            }

            Section {
                width: parent.width
                label: "Grenzen"

                Row {
                    width: parent.width
                    spacing: Theme.gap + Theme.unit / 2

                    TimecodeField {
                        objectName: "startField"
                        width: (parent.width - Theme.gap - Theme.unit / 2) / 2
                        label: "Start"
                        which: "start"
                        value: workspace.draftStartText
                    }

                    TimecodeField {
                        objectName: "endField"
                        width: (parent.width - Theme.gap - Theme.unit / 2) / 2
                        label: "Ende"
                        which: "end"
                        value: workspace.draftEndText
                    }
                }

                // The live duration readout: the number being edited, to the
                // hundredth, which is the precision the Clip list drops.
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
                        objectName: "durationReadout"
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

            Section {
                width: parent.width
                label: "Notizen"
                lastSection: true

                Rectangle {
                    width: parent.width
                    height: Theme.editorNotesHeight
                    radius: Theme.radius
                    color: Theme.control
                    border.width: Theme.border
                    border.color: notes.activeFocus ? Theme.accent : Theme.controlBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: Theme.gap + Theme.unit / 2
                        clip: true
                        contentHeight: notes.contentHeight

                        TextEdit {
                            id: notes

                            objectName: "notesField"
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

                            // An empty box is a mystery; this says what it is
                            // for until there is something in it.
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

    // --- The action row: one accent primary and one quiet secondary --------

    Rectangle {
        id: actionsRule
        anchors { bottom: actions.top; left: parent.left; right: parent.right }
        anchors.leftMargin: Theme.border
        height: Theme.border
        color: Theme.rule
    }

    Item {
        id: actions
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: Theme.editorActionsHeight

        Text {
            objectName: "draftError"
            anchors {
                left: parent.left
                leftMargin: Theme.gutter
                verticalCenter: parent.verticalCenter
            }
            anchors.right: buttons.left
            anchors.rightMargin: Theme.gap
            visible: workspace.draftError !== ""
            text: workspace.draftError
            elide: Text.ElideRight
            color: Theme.warning
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeLabel
            font.weight: Theme.regular
        }

        Row {
            id: buttons
            anchors {
                right: parent.right
                rightMargin: Theme.gutter
                verticalCenter: parent.verticalCenter
            }
            spacing: Theme.gap

            TextButton {
                objectName: "cancelButton"
                label: "Abbrechen"
                onClicked: workspace.cancelDraft()
            }

            TextButton {
                objectName: "saveButton"
                primary: true
                label: workspace.draftIsNew ? "Clip anlegen" : "Übernehmen"
                enabled: workspace.draftValid
                onClicked: workspace.commitDraft()
            }
        }
    }
}
