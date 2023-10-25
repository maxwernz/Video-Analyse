# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/max/development/video_player/clip_handler.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.clipDuration = QtWidgets.QLabel(Dialog)
        self.clipDuration.setObjectName("clipDuration")
        self.horizontalLayout.addWidget(self.clipDuration)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.clipNameLine = QtWidgets.QLineEdit(Dialog)
        self.clipNameLine.setObjectName("clipNameLine")
        self.verticalLayout.addWidget(self.clipNameLine)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.notesText = QtWidgets.QTextEdit(Dialog)
        self.notesText.setObjectName("notesText")
        self.verticalLayout.addWidget(self.notesText)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.categoryBox = QtWidgets.QComboBox(Dialog)
        self.categoryBox.setEditable(True)
        self.categoryBox.setObjectName("categoryBox")
        self.verticalLayout.addWidget(self.categoryBox)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.cancelButton = QtWidgets.QPushButton(Dialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout_2.addWidget(self.cancelButton)
        self.acceptButton = QtWidgets.QPushButton(Dialog)
        self.acceptButton.setDefault(True)
        self.acceptButton.setObjectName("acceptButton")
        self.horizontalLayout_2.addWidget(self.acceptButton)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_3.setText(_translate("Dialog", "Clip Titel"))
        self.clipDuration.setText(_translate("Dialog", "TextLabel"))
        self.label_2.setText(_translate("Dialog", "Notizen"))
        self.label.setText(_translate("Dialog", "Kategorie"))
        self.cancelButton.setText(_translate("Dialog", "Cancel"))
        self.acceptButton.setText(_translate("Dialog", "OK"))