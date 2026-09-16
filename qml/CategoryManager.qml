import QtQuick
import "."

/*
  Category management lives in the sidebar, not in a modal: an analyst can
  compare the durable Analysis-wide collection with the current workspace
  without a second window taking over the review. The template scope names
  future Analyses explicitly, because changing it must never imply a rewrite
  of the Analysis already open.
*/
Rectangle {
    id: root
    objectName: "categoryManager"
    visible: workspace.managingCategories
    color: Theme.panel

    Column {
        anchors { fill: parent; margins: Theme.gutter }
        spacing: Theme.gap

        Row {
            width: parent.width
            spacing: Theme.gap

            Text {
                text: workspace.categoryManagementScope === "analysis"
                      ? "Kategorien dieser Analyse"
                      : "Vorlage für neue Analysen"
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeTitle
                font.weight: Theme.medium
                width: parent.width - closeButton.width - Theme.gap
                elide: Text.ElideRight
            }

            IconButton {
                id: closeButton
                iconName: "x"
                tooltip: "Kategorien schließen"
                onClicked: workspace.closeCategoryManagement()
            }
        }

        Row {
            spacing: Theme.gap

            TextButton {
                label: "Analyse"
                primary: workspace.categoryManagementScope === "analysis"
                onClicked: workspace.setCategoryManagementScope("analysis")
            }
            TextButton {
                label: "Vorlage"
                primary: workspace.categoryManagementScope === "template"
                onClicked: workspace.setCategoryManagementScope("template")
            }
        }

        Text {
            width: parent.width
            visible: workspace.categoryManagementScope === "template"
            text: "Gilt nur für künftig angelegte Analysen."
            wrapMode: Text.WordWrap
            color: Theme.textMuted
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeBody
        }

        ListView {
            id: categories
            objectName: "managedCategoryList"
            width: parent.width
            height: parent.height - y - actions.height - Theme.gap
            clip: true
            model: workspace.managedCategoryModel
            boundsBehavior: Flickable.StopAtBounds
            ScrollHint { flickable: categories }

            delegate: Item {
                id: categoryRow
                objectName: "managedCategoryRow"
                required property var model
                required property int index
                property bool removeArmed: false

                width: categories.width
                height: Theme.sourceRowHeight

                Timer {
                    id: disarmTimer
                    interval: 3000
                    onTriggered: categoryRow.removeArmed = false
                }

                Rectangle {
                    anchors.fill: parent
                    color: rowArea.containsMouse ? Theme.controlSubtleHover : "transparent"
                }

                // This full-row area is deliberately declared before every
                // input control below. The colour choice, name editor and
                // armed removal all therefore receive their own clicks.
                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                }

                Rectangle {
                    id: colour
                    anchors { left: parent.left; leftMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
                    width: Theme.categoryDotSize * 2
                    height: width
                    radius: width / 2
                    color: categoryRow.model.color

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: workspace.cycleManagedCategoryColor(categoryRow.model.categoryId)
                    }
                }

                TextInput {
                    id: nameField
                    anchors {
                        left: colour.right
                        leftMargin: Theme.gap
                        right: rowActions.left
                        rightMargin: Theme.gap
                        verticalCenter: parent.verticalCenter
                    }
                    text: categoryRow.model.name
                    visible: !categoryRow.removeArmed
                    selectByMouse: true
                    color: Theme.text
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeRow
                    font.weight: Theme.medium
                    onEditingFinished: workspace.setManagedCategoryName(
                                           categoryRow.model.categoryId, text)
                }

                // Deletion is armed in-place. The row states what happens to
                // affected Clips, so confirmation does not depend on a tooltip
                // or a Dialog appearing between the two clicks.
                Text {
                    objectName: "categoryRemovalWarning"
                    visible: categoryRow.removeArmed
                    anchors {
                        left: colour.right
                        leftMargin: Theme.gap
                        right: rowActions.left
                        rightMargin: Theme.gap
                        verticalCenter: parent.verticalCenter
                    }
                    text: workspace.categoryManagementScope === "analysis"
                          ? "Entfernen? " + categoryRow.model.clipCount
                            + (categoryRow.model.clipCount === 1
                               ? " Clip bleibt ohne Kategorie."
                               : " Clips bleiben ohne Kategorie.")
                          : "Aus Vorlage entfernen? Bestehende Analysen bleiben unverändert."
                    elide: Text.ElideRight
                    color: Theme.warning
                    font.family: Theme.uiFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Theme.medium
                }

                Row {
                    id: rowActions
                    anchors { right: parent.right; rightMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
                    spacing: 0
                    visible: rowArea.containsMouse || categoryRow.removeArmed

                    IconButton {
                        iconName: "chevron-down"
                        rotation: 180
                        tooltip: "Nach oben verschieben"
                        enabled: categoryRow.index > 0
                        onClicked: workspace.moveManagedCategoryEarlier(categoryRow.model.categoryId)
                    }
                    IconButton {
                        iconName: "chevron-down"
                        tooltip: "Nach unten verschieben"
                        enabled: categoryRow.index < categories.count - 1
                        onClicked: workspace.moveManagedCategoryLater(categoryRow.model.categoryId)
                    }
                    IconButton {
                        objectName: "managedCategoryRemove"
                        iconName: "trash-2"
                        tooltip: categoryRow.removeArmed ? "Entfernen bestätigen" : "Kategorie entfernen"
                        iconColor: categoryRow.removeArmed ? Theme.warning : Theme.textMuted
                        onClicked: {
                            if (categoryRow.removeArmed) {
                                disarmTimer.stop()
                                categoryRow.removeArmed = false
                                workspace.removeManagedCategory(categoryRow.model.categoryId)
                            } else {
                                categoryRow.removeArmed = true
                                disarmTimer.restart()
                            }
                        }
                    }
                }
            }
        }

        Text {
            width: parent.width
            visible: workspace.categoryError !== ""
            text: workspace.categoryError
            wrapMode: Text.WordWrap
            color: Theme.warning
            font.family: Theme.uiFamily
            font.pixelSize: Theme.sizeBody
        }

        Row {
            id: actions
            spacing: Theme.gap

            TextButton {
                label: "Kategorie hinzufügen"
                iconName: "plus"
                onClicked: workspace.addManagedCategory()
            }
            TextButton {
                visible: workspace.categoryManagementScope === "template"
                label: "Handball-Vorlage wiederherstellen"
                iconName: "rotate-ccw"
                onClicked: workspace.restoreCategoryTemplate()
            }
        }
    }
}
