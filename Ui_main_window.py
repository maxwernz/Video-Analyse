# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/max/development/video_player/main_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1558, 814)
        MainWindow.setAcceptDrops(True)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setMouseTracking(True)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.treeWidget = TreeWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setAcceptDrops(True)
        self.treeWidget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.header().setCascadingSectionResizes(False)
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.titleLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        font.setWeight(75)
        self.titleLabel.setFont(font)
        self.titleLabel.setIndent(10)
        self.titleLabel.setObjectName("titleLabel")
        self.verticalLayout.addWidget(self.titleLabel)
        self.videoWidget = VideoWidget(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.videoWidget.sizePolicy().hasHeightForWidth())
        self.videoWidget.setSizePolicy(sizePolicy)
        self.videoWidget.setAcceptDrops(True)
        self.videoWidget.setObjectName("videoWidget")
        self.verticalLayout.addWidget(self.videoWidget)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.soundButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.soundButton.setText("")
        self.soundButton.setIconSize(QtCore.QSize(20, 20))
        self.soundButton.setCheckable(True)
        self.soundButton.setChecked(False)
        self.soundButton.setAutoDefault(False)
        self.soundButton.setDefault(False)
        self.soundButton.setFlat(False)
        self.soundButton.setObjectName("soundButton")
        self.horizontalLayout_2.addWidget(self.soundButton)
        self.backwardButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.backwardButton.setText("")
        self.backwardButton.setIconSize(QtCore.QSize(20, 20))
        self.backwardButton.setObjectName("backwardButton")
        self.horizontalLayout_2.addWidget(self.backwardButton)
        self.playPauseButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.playPauseButton.setText("")
        self.playPauseButton.setIconSize(QtCore.QSize(20, 20))
        self.playPauseButton.setCheckable(True)
        self.playPauseButton.setChecked(False)
        self.playPauseButton.setObjectName("playPauseButton")
        self.horizontalLayout_2.addWidget(self.playPauseButton)
        self.forwardButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.forwardButton.setText("")
        self.forwardButton.setIconSize(QtCore.QSize(20, 20))
        self.forwardButton.setObjectName("forwardButton")
        self.horizontalLayout_2.addWidget(self.forwardButton)
        self.label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/gauge.open.with.lines.needle.33percent.svg"))
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.speedBox = QtWidgets.QComboBox(self.verticalLayoutWidget)
        self.speedBox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.speedBox.setIconSize(QtCore.QSize(16, 16))
        self.speedBox.setObjectName("speedBox")
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.horizontalLayout_2.addWidget(self.speedBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.clipButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.clipButton.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/record.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap("/Users/max/development/video_player/icons/record_action.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.clipButton.setIcon(icon)
        self.clipButton.setIconSize(QtCore.QSize(20, 20))
        self.clipButton.setCheckable(True)
        self.clipButton.setChecked(False)
        self.clipButton.setObjectName("clipButton")
        self.horizontalLayout_2.addWidget(self.clipButton)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout.addWidget(self.splitter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1558, 24))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuBearbeiten = QtWidgets.QMenu(self.menubar)
        self.menuBearbeiten.setObjectName("menuBearbeiten")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoad_Video = QtWidgets.QAction(MainWindow)
        self.actionLoad_Video.setObjectName("actionLoad_Video")
        self.actionAnalyse_laden = QtWidgets.QAction(MainWindow)
        self.actionAnalyse_laden.setObjectName("actionAnalyse_laden")
        self.actionAnalyse_speichern = QtWidgets.QAction(MainWindow)
        self.actionAnalyse_speichern.setObjectName("actionAnalyse_speichern")
        self.actionClips_Exportieren = QtWidgets.QAction(MainWindow)
        self.actionClips_Exportieren.setObjectName("actionClips_Exportieren")
        self.actionAnalyse_entfernen = QtWidgets.QAction(MainWindow)
        self.actionAnalyse_entfernen.setObjectName("actionAnalyse_entfernen")
        self.actionVideo_Exportieren = QtWidgets.QAction(MainWindow)
        self.actionVideo_Exportieren.setObjectName("actionVideo_Exportieren")
        self.menuFile.addAction(self.actionLoad_Video)
        self.menuFile.addAction(self.actionAnalyse_laden)
        self.menuFile.addAction(self.actionAnalyse_speichern)
        self.menuFile.addAction(self.actionClips_Exportieren)
        self.menuFile.addAction(self.actionVideo_Exportieren)
        self.menuBearbeiten.addAction(self.actionAnalyse_entfernen)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuBearbeiten.menuAction())

        self.retranslateUi(MainWindow)
        self.speedBox.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Video Analyse"))
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.headerItem().setText(0, _translate("MainWindow", "Clip"))
        self.treeWidget.headerItem().setText(1, _translate("MainWindow", "Start"))
        self.treeWidget.headerItem().setText(2, _translate("MainWindow", "Stop"))
        self.titleLabel.setText(_translate("MainWindow", "No Video"))
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
        self.menuFile.setTitle(_translate("MainWindow", "Datei"))
        self.menuBearbeiten.setTitle(_translate("MainWindow", "Bearbeiten"))
        self.actionLoad_Video.setText(_translate("MainWindow", "Video laden"))
        self.actionLoad_Video.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionAnalyse_laden.setText(_translate("MainWindow", "Analyse laden"))
        self.actionAnalyse_laden.setShortcut(_translate("MainWindow", "Ctrl+Shift+O"))
        self.actionAnalyse_speichern.setText(_translate("MainWindow", "Analyse speichern"))
        self.actionAnalyse_speichern.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionClips_Exportieren.setText(_translate("MainWindow", "Clips Exportieren"))
        self.actionClips_Exportieren.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.actionAnalyse_entfernen.setText(_translate("MainWindow", "Analyse entfernen"))
        self.actionVideo_Exportieren.setText(_translate("MainWindow", "Video Exportieren"))
        self.actionVideo_Exportieren.setShortcut(_translate("MainWindow", "Ctrl+Shift+E"))
from treewidget import TreeWidget
from videowidget import VideoWidget
