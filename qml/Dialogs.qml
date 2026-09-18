import QtQuick
import QtQuick.Dialogs
import "."

/*
  Every dialog `WorkspacePresenter` can ask for, drawn once and instantiated
  once, in `Main.qml`.

  Issue #69: an `exec()`'d `QFileDialog` or `QMessageBox` self-cancels within
  a few seconds of opening whenever the OS mouse cursor is resting over a
  hover-tracked `QQuickItem`, which on this application's own toolbar is the
  ordinary way an analyst reaches Open, Save As or Add Source video rather
  than a corner case. The one dialog technology found immune is
  `QtQuick.Dialogs.FileDialog` — still a real native panel on macOS, so ADR
  0007's native-*behaviour* promise holds — and it is asynchronous by
  construction, which is why the chooser below reports back through
  `presenter`'s slots instead of a return value.

  The yes/no/report questions were never a native surface to begin with —
  `QMessageBox.exec()` self-cancels on hover exactly like the file dialogs —
  so they are drawn here from this application's own primitives rather than
  from `QtWidgets` at all. They are not Qt Quick Controls either: a stock
  `Dialog` would be exactly the restyled-platform-control failure ADR 0007
  exists to avoid.
*/
Item {
    id: root
    anchors.fill: parent
    readonly property bool questionVisible: question.visible

    // --- The file chooser: still the platform's own -----------------------

    FileDialog {
        id: fileDialog
        objectName: "fileDialog"
        title: presenter.fileDialogTitle
        nameFilters: [presenter.fileDialogFilter]
        fileMode: presenter.fileDialogMode === "save" ? FileDialog.SaveFile
                                                       : FileDialog.OpenFile
        onAccepted: presenter.fileDialogAccepted(selectedFile)
        onRejected: presenter.fileDialogCancelled()
    }

    Connections {
        target: presenter
        function onFileDialogRequested() {
            if (presenter.fileDialogFolder !== "")
                fileDialog.currentFolder = "file://" + presenter.fileDialogFolder
            else
                fileDialog.currentFolder = ""
            if (presenter.fileDialogSuggestedName !== "")
                // No folder is not a reason to drop the suggested name too:
                // `_existing_start_directory` returns "" for a real,
                // unmounted location (an iCloud Documents folder, say),
                // exactly when a suggested name still matters. The bare
                // name, with no folder prefixed, is what the previous
                // `QFileDialog` accepted the same way — `os.path.join("",
                // name) == name` — and lets the platform pick where to
                // start instead of guessing wrong.
                fileDialog.selectedFile = presenter.fileDialogFolder === ""
                    ? presenter.fileDialogSuggestedName
                    : "file://" + presenter.fileDialogFolder
                        + "/" + presenter.fileDialogSuggestedName
            else
                fileDialog.selectedFile = ""
            fileDialog.open()
        }
    }

    // --- A yes/no/report-shaped question, drawn as this application's own -

    Rectangle {
        id: scrim
        anchors.fill: parent
        color: Theme.pendingScrim
        z: Theme.dialogLayer
        visible: question.visible

        // A visual scrim does not make an Item modal: without this input
        // layer, a click outside the question falls through to the workspace
        // and can start another command while `_question_callback` is still
        // pending. Keep the blocker in the same layer as the scrim, below the
        // question (whose z is one higher) and above every workspace surface.
        MouseArea {
            anchors.fill: parent
            preventStealing: true
            acceptedButtons: Qt.AllButtons
        }
    }

    Rectangle {
        id: question
        objectName: "questionDialog"
        anchors.centerIn: parent
        width: Theme.dialogWidth
        radius: Theme.radius
        color: Theme.panel
        border.width: Theme.border
        border.color: Theme.rule
        z: Theme.dialogLayer + 1
        visible: false
        height: body.implicitHeight + Theme.gutter * 2

        property var buttonModel: []

        Column {
            id: body
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.gutter }
            spacing: Theme.gutter

            Text {
                objectName: "questionTitle"
                width: parent.width
                text: presenter.questionTitle
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeTitle
                font.weight: Theme.medium
                wrapMode: Text.WordWrap
            }

            Text {
                objectName: "questionText"
                width: parent.width
                text: presenter.questionText
                color: Theme.textMuted
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeBody
                wrapMode: Text.WordWrap
            }

            Row {
                anchors.right: parent.right
                spacing: Theme.gap
                layoutDirection: Qt.RightToLeft

                Repeater {
                    objectName: "questionRepeater"
                    model: question.buttonModel
                    delegate: TextButton {
                        objectName: "questionButton_" + modelData.id
                        label: modelData.text
                        primary: !!modelData.default
                        onClicked: question.answer(modelData.id)
                    }
                }
            }
        }

        Shortcut {
            sequence: "Escape"
            enabled: question.visible
            onActivated: question.dismiss()
        }

        // These are the `default` and `cancel` semantics the previous
        // QMessageBox carried. A custom QML question does not get either
        // behaviour for free, so route both Return spellings explicitly,
        // and route Escape (and any other dismissal) through whichever
        // button in `buttonModel` is marked `cancel`, exactly the way
        // `answerDefault` below routes Return through whichever is marked
        // `default`.
        Shortcut {
            sequence: "Return"
            enabled: question.visible
            onActivated: question.answerDefault()
        }

        Shortcut {
            sequence: "Enter"
            enabled: question.visible
            onActivated: question.answerDefault()
        }

        function answer(buttonId) {
            question.visible = false
            presenter.questionAnswered(buttonId)
        }

        function answerDefault() {
            for (let index = 0; index < question.buttonModel.length; index += 1) {
                if (question.buttonModel[index].default) {
                    question.answer(question.buttonModel[index].id)
                    return
                }
            }
            question.dismiss()
        }

        function dismiss() {
            for (let index = 0; index < question.buttonModel.length; index += 1) {
                if (question.buttonModel[index].cancel) {
                    question.answer(question.buttonModel[index].id)
                    return
                }
            }
            question.answer("")
        }
    }

    Connections {
        target: presenter
        function onQuestionRequested() {
            question.buttonModel = presenter.questionButtons
            question.visible = true
        }
    }

    // --- A non-blocking failure notice -------------------------------------

    Rectangle {
        id: failure
        objectName: "failureDialog"
        anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: Theme.gutter }
        width: Theme.dialogWidth
        radius: Theme.radius
        color: Theme.panel
        border.width: Theme.border
        border.color: Theme.rule
        z: Theme.dialogLayer + 1
        // Bound straight to the presenter's queue rather than latched by a
        // local boolean on `failureRequested`: a second failure reported
        // while this one is still showing re-emits that signal with the
        // queue still non-empty (nothing to change here), and dismissing
        // the last one needs this to go back to false on its own once the
        // queue empties — a one-shot "show it" signal cannot express that.
        visible: presenter.failurePending
        height: failureBody.implicitHeight + Theme.gutter * 2

        Column {
            id: failureBody
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.gutter }
            spacing: Theme.gap

            Text {
                objectName: "failureTitle"
                width: parent.width
                text: presenter.failureTitle
                color: Theme.text
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeTitle
                font.weight: Theme.medium
                wrapMode: Text.WordWrap
            }

            Text {
                objectName: "failureMessage"
                width: parent.width
                text: presenter.failureMessage
                color: Theme.textMuted
                font.family: Theme.uiFamily
                font.pixelSize: Theme.sizeBody
                wrapMode: Text.WordWrap
            }

            Row {
                anchors.right: parent.right
                TextButton {
                    objectName: "failureDismiss"
                    label: "OK"
                    primary: true
                    onClicked: presenter.failureDismissed()
                }
            }
        }
    }
}
