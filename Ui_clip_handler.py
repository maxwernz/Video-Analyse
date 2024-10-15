# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'clip_handler.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTextEdit, QVBoxLayout, QWidget)
import resources_rc

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(400, 351)
        Dialog.setStyleSheet(u"/* Style for the QDialog */\n"
"QDialog {\n"
"    background-color: rgb(31, 31, 31); /* Dark background */\n"
"    border: 2px solid rgb(65, 65, 65); /* Border around the window */\n"
"    border-top-left-radius: 0px; /* No radius on top left */\n"
"    border-top-right-radius: 0px; /* No radius on top right */\n"
"    border-bottom-left-radius: 10px; /* Rounded bottom left */\n"
"    border-bottom-right-radius: 10px; /* Rounded bottom right */\n"
"    padding: 10px; /* Padding inside the window */\n"
"}\n"
"\n"
"/* QLabel styling */\n"
"QLabel {\n"
"    color: white; /* White text for labels */\n"
"    font: 14px \"Segoe UI\", sans-serif; /* Modern font */\n"
"    padding: 5px;\n"
"}\n"
"\n"
"/* QLineEdit styling (Clip name input field) */\n"
"QLineEdit {\n"
"    background-color: rgb(45, 45, 45); /* Slightly lighter background for input */\n"
"    color: white; /* White text */\n"
"    border: 2px solid rgb(65, 65, 65);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    font: 14px \"Segoe UI\", sans-s"
                        "erif;\n"
"}\n"
"\n"
"/* QTextEdit styling (Notes input field) */\n"
"QTextEdit {\n"
"    background-color: rgb(45, 45, 45);\n"
"    color: white;\n"
"    border: 2px solid rgb(65, 65, 65);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    font: 14px \"Segoe UI\", sans-serif;\n"
"}\n"
"\n"
"/* QComboBox styling */\n"
"QComboBox {\n"
"    border: 2px solid rgb(65, 65, 65); /* Border for combo box */\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    background-color: rgb(31, 31, 31); /* Dark background */\n"
"    color: white;\n"
"    font: 14px \"Segoe UI\", sans-serif;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    border: none;\n"
"    width: 30px;                    /* Width of the drop-down button */\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"	image: url(:/icons/chevron.down.square.png);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    background-color: rgb(31, 31, 31); /* Background of the drop-down list */\n"
"    color: white; /* Text color */\n"
""
                        "    border: 2px solid rgb(65, 65, 65); /* Border around drop-down */\n"
"    selection-background-color: rgb(66, 65, 64); /* Highlight color for selected item */\n"
"}\n"
"\n"
"/* QPushButton styling */\n"
"QPushButton {\n"
"    background-color: rgb(45, 45, 45); /* Button background */\n"
"    color: white; /* Button text color */\n"
"    border: 2px solid rgb(65, 65, 65); /* Border color */\n"
"    border-radius: 5px; /* Rounded corners */\n"
"    padding: 8px;\n"
"    font: 14px \"Segoe UI\", sans-serif;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(66, 65, 64); /* Change background on hover */\n"
"    border: 2px solid rgb(80, 80, 80); /* Slightly lighter border on hover */\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(100, 100, 100); /* Darker background on press */\n"
"    border: 2px solid rgb(80, 80, 80);\n"
"}\n"
"")
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_3 = QLabel(Dialog)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.clipDuration = QLabel(Dialog)
        self.clipDuration.setObjectName(u"clipDuration")

        self.horizontalLayout.addWidget(self.clipDuration)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.clipNameLine = QLineEdit(Dialog)
        self.clipNameLine.setObjectName(u"clipNameLine")

        self.verticalLayout.addWidget(self.clipNameLine)

        self.label_2 = QLabel(Dialog)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.notesText = QTextEdit(Dialog)
        self.notesText.setObjectName(u"notesText")

        self.verticalLayout.addWidget(self.notesText)

        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.categoryBox = QComboBox(Dialog)
        self.categoryBox.setObjectName(u"categoryBox")
        self.categoryBox.setEditable(True)

        self.verticalLayout.addWidget(self.categoryBox)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.cancelButton = QPushButton(Dialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout_2.addWidget(self.cancelButton)

        self.acceptButton = QPushButton(Dialog)
        self.acceptButton.setObjectName(u"acceptButton")

        self.horizontalLayout_2.addWidget(self.acceptButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(Dialog)

        self.acceptButton.setDefault(True)


        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"Clip Titel", None))
        self.clipDuration.setText(QCoreApplication.translate("Dialog", u"TextLabel", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Notizen", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Kategorie", None))
        self.cancelButton.setText(QCoreApplication.translate("Dialog", u"Cancel", None))
        self.acceptButton.setText(QCoreApplication.translate("Dialog", u"OK", None))
    # retranslateUi

