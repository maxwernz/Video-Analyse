# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/max/development/video_player/main_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1558, 814)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setMouseTracking(True)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.treeWidget = QtWidgets.QTreeWidget(self.centralwidget)
        self.treeWidget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.header().setCascadingSectionResizes(False)
        self.horizontalLayout.addWidget(self.treeWidget)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.videoWidget = VideoWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.videoWidget.sizePolicy().hasHeightForWidth())
        self.videoWidget.setSizePolicy(sizePolicy)
        self.videoWidget.setObjectName("videoWidget")
        self.verticalLayout.addWidget(self.videoWidget)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.soundButton = QtWidgets.QPushButton(self.centralwidget)
        self.soundButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/mute.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/sound.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.soundButton.setIcon(icon)
        self.soundButton.setIconSize(QtCore.QSize(32, 32))
        self.soundButton.setCheckable(True)
        self.soundButton.setChecked(False)
        self.soundButton.setAutoDefault(False)
        self.soundButton.setDefault(False)
        self.soundButton.setFlat(False)
        self.soundButton.setObjectName("soundButton")
        self.horizontalLayout_2.addWidget(self.soundButton)
        self.backwardButton = QtWidgets.QPushButton(self.centralwidget)
        self.backwardButton.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/backward.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.backwardButton.setIcon(icon1)
        self.backwardButton.setIconSize(QtCore.QSize(32, 32))
        self.backwardButton.setObjectName("backwardButton")
        self.horizontalLayout_2.addWidget(self.backwardButton)
        self.playPauseButton = QtWidgets.QPushButton(self.centralwidget)
        self.playPauseButton.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/play.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon2.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/pause.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.playPauseButton.setIcon(icon2)
        self.playPauseButton.setIconSize(QtCore.QSize(32, 32))
        self.playPauseButton.setCheckable(True)
        self.playPauseButton.setChecked(False)
        self.playPauseButton.setObjectName("playPauseButton")
        self.horizontalLayout_2.addWidget(self.playPauseButton)
        self.forwardButton = QtWidgets.QPushButton(self.centralwidget)
        self.forwardButton.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/forward.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.forwardButton.setIcon(icon3)
        self.forwardButton.setIconSize(QtCore.QSize(32, 32))
        self.forwardButton.setObjectName("forwardButton")
        self.horizontalLayout_2.addWidget(self.forwardButton)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/gauge.open.with.lines.needle.33percent.svg"))
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.speedBox = QtWidgets.QComboBox(self.centralwidget)
        self.speedBox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.speedBox.setIconSize(QtCore.QSize(16, 16))
        self.speedBox.setObjectName("speedBox")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/tortoise_025.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.speedBox.addItem(icon4, "")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/tortoise_05.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.speedBox.addItem(icon5, "")
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/video.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.speedBox.addItem(icon6, "")
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/rabbit.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.speedBox.addItem(icon7, "")
        self.horizontalLayout_2.addWidget(self.speedBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.clipButton = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.clipButton.setFont(font)
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/record.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon8.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/record_action.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.clipButton.setIcon(icon8)
        self.clipButton.setIconSize(QtCore.QSize(32, 32))
        self.clipButton.setCheckable(True)
        self.clipButton.setChecked(False)
        self.clipButton.setObjectName("clipButton")
        self.horizontalLayout_2.addWidget(self.clipButton)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout.setStretch(0, 1)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.horizontalLayout.setStretch(1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1558, 24))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoad_Video = QtWidgets.QAction(MainWindow)
        self.actionLoad_Video.setObjectName("actionLoad_Video")
        self.menuFile.addAction(self.actionLoad_Video)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        self.speedBox.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.headerItem().setText(0, _translate("MainWindow", "Clip"))
        self.treeWidget.headerItem().setText(1, _translate("MainWindow", "Start"))
        self.treeWidget.headerItem().setText(2, _translate("MainWindow", "Stop"))
        self.soundButton.setShortcut(_translate("MainWindow", "M"))
        self.backwardButton.setShortcut(_translate("MainWindow", "Ctrl+Left"))
        self.playPauseButton.setShortcut(_translate("MainWindow", "Space"))
        self.forwardButton.setShortcut(_translate("MainWindow", "Ctrl+Right"))
        self.speedBox.setItemText(0, _translate("MainWindow", "0.25x"))
        self.speedBox.setItemText(1, _translate("MainWindow", "0.5x"))
        self.speedBox.setItemText(2, _translate("MainWindow", "1x"))
        self.speedBox.setItemText(3, _translate("MainWindow", "2x"))
        self.clipButton.setText(_translate("MainWindow", "Clip"))
        self.clipButton.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionLoad_Video.setText(_translate("MainWindow", "Load Video"))
from videowidget import VideoWidget
