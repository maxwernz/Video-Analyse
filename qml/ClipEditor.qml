import QtQuick
import "."

/* One editor for a new Pending Clip and for an existing Clip. */
Rectangle {
    id: root
    implicitWidth: Theme.editorWidth
    color: Theme.panel

    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Theme.border
        color: Theme.rule
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: Theme.toolbarHeight
        Text {
            anchors { verticalCenter: parent.verticalCenter; left: parent.left }
            anchors.leftMargin: Theme.gutter
            text: workspace.draftIsNew ? "Neuer Clip" : "Clip bearbeiten"
            color: Theme.text
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeTitle
            font.weight: Theme.medium
        }
        IconButton {
            anchors { verticalCenter: parent.verticalCenter; right: parent.right }
            anchors.rightMargin: Theme.gutter
            iconName: "x"
            tooltip: "Abbrechen"
            onClicked: workspace.cancelDraft()
        }
    }

    Rectangle {
        id: headerRule
        anchors { top: header.bottom; left: parent.left; right: parent.right }
        height: Theme.border
        color: Theme.rule
    }

    Flickable {
        id: form
        anchors { top: headerRule.bottom; left: parent.left; right: parent.right; bottom: actionsRule.top }
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
                    spacing: Theme.gap
                    Repeater {
                        model: workspace.categoryModel
                        Item {
                            required property var model
                            width: chipRow.implicitWidth + Theme.controlPadding * 2
                            height: Theme.editorCategoryHeight
                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radius
                                color: model.selected ? Theme.selection
                                      : chipArea.containsMouse ? Theme.controlHover : Theme.control
                                border.width: Theme.border
                                border.color: model.selected ? Theme.accent : Theme.controlBorder
                            }
                            Row {
                                id: chipRow
                                anchors.centerIn: parent
                                spacing: Theme.gap
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: Theme.editorCategoryDotSize
                                    height: Theme.editorCategoryDotSize
                                    radius: width / 2
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

            Section {
                width: parent.width
                label: "Grenzen"
                Row {
                    width: parent.width
                    spacing: Theme.gap
                    TimecodeField {
                        width: (parent.width - Theme.gap) / 2
                        label: "Start"
                        which: "start"
                        value: workspace.draftStartText
                    }
                    TimecodeField {
                        width: (parent.width - Theme.gap) / 2
                        label: "Ende"
                        which: "end"
                        value: workspace.draftEndText
                    }
                }
                Row {
                    width: parent.width
                    spacing: Theme.gap
                    Text {
                        text: "Dauer"
                        color: Theme.textMuted
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeLabel
                        font.weight: Theme.medium
                    }
                    Text {
                        text: workspace.draftDurationText
                        color: Theme.text
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.sizeTimecode
                        font.weight: Theme.medium
                    }
                    Text {
                        text: "· bewegt das Video mit"
                        color: Theme.textFaint
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeLabel
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
                    TextEdit {
                        id: notes
                        anchors.fill: parent
                        anchors.margins: Theme.gap
                        text: workspace.draftNotes
                        wrapMode: TextEdit.Wrap
                        color: Theme.text
                        selectionColor: Theme.accent
                        selectedTextColor: Theme.accentOn
                        font.family: Theme.uiFamily
                        font.pixelSize: Theme.sizeBody
                        onTextChanged: workspace.setDraftNotes(text)
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

    Rectangle {
        id: actionsRule
        anchors { bottom: actions.top; left: parent.left; right: parent.right }
        height: Theme.border
        color: Theme.rule
    }

    Item {
        id: actions
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: Theme.editorActionHeight
        Text {
            anchors { left: parent.left; leftMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
            anchors.right: buttons.left
            anchors.rightMargin: Theme.gap
            visible: workspace.draftError !== ""
            text: workspace.draftError
            elide: Text.ElideRight
            color: Theme.categoryPalette[1]
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeLabel
        }
        Row {
            id: buttons
            anchors { right: parent.right; rightMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
            spacing: Theme.gap
            TextButton { label: "Abbrechen"; onClicked: workspace.cancelDraft() }
            TextButton {
                primary: true
                label: workspace.draftIsNew ? "Clip anlegen" : "Übernehmen"
                enabled: workspace.draftValid
                onClicked: workspace.commitDraft()
            }
        }
    }
}
