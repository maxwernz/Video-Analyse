# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QComboBox,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMenu, QMenuBar, QPushButton,
    QSizePolicy, QSpacerItem, QSplitter, QStatusBar,
    QTreeWidgetItem, QVBoxLayout, QWidget)

from treewidget import TreeWidget
from videowidget import VideoWidget
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1841, 1106)
        MainWindow.setAcceptDrops(True)
        MainWindow.setStyleSheet(u"background-color: rgb(31, 31, 31);\n"
"color: rgb(255, 255, 255);\n"
"font: \"SF Pro\";\n"
"")
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.actionLoad_Video = QAction(MainWindow)
        self.actionLoad_Video.setObjectName(u"actionLoad_Video")
        self.actionAnalyse_laden = QAction(MainWindow)
        self.actionAnalyse_laden.setObjectName(u"actionAnalyse_laden")
        self.actionAnalyse_speichern = QAction(MainWindow)
        self.actionAnalyse_speichern.setObjectName(u"actionAnalyse_speichern")
        self.actionClips_Exportieren = QAction(MainWindow)
        self.actionClips_Exportieren.setObjectName(u"actionClips_Exportieren")
        self.actionAnalyse_entfernen = QAction(MainWindow)
        self.actionAnalyse_entfernen.setObjectName(u"actionAnalyse_entfernen")
        self.actionVideo_Exportieren = QAction(MainWindow)
        self.actionVideo_Exportieren.setObjectName(u"actionVideo_Exportieren")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setEnabled(True)
        self.centralwidget.setMouseTracking(True)
        self.centralwidget.setStyleSheet(u"QPushButton{\n"
"border: none;\n"
"}")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setStyleSheet(u"border-color: rgb(0, 0, 0);")
        self.splitter.setOrientation(Qt.Horizontal)
        self.treeWidget = TreeWidget(self.splitter)
        self.treeWidget.setObjectName(u"treeWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setAcceptDrops(True)
        self.treeWidget.setStyleSheet(u"background-color: rgb(55, 55, 55);\n"
"gridline-color: rgb(255, 126, 227);\n"
"color: rgb(255, 255, 255);\n"
"border-color: rgb(40, 40, 40);\n"
"font: 15px;\n"
"")
        self.treeWidget.setFrameShape(QFrame.StyledPanel)
        self.treeWidget.setFrameShadow(QFrame.Sunken)
        self.treeWidget.setLineWidth(4)
        self.treeWidget.setMidLineWidth(1)
        self.treeWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.treeWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeWidget.setSortingEnabled(True)
        self.splitter.addWidget(self.treeWidget)
        self.treeWidget.header().setVisible(True)
        self.treeWidget.header().setCascadingSectionResizes(False)
        self.treeWidget.header().setHighlightSections(False)
        self.verticalLayoutWidget = QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.titleLabel = QLabel(self.verticalLayoutWidget)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setPointSize(20)
        font.setBold(False)
        font.setItalic(False)
        self.titleLabel.setFont(font)
        self.titleLabel.setIndent(10)

        self.verticalLayout.addWidget(self.titleLabel)

        self.videoWidget = VideoWidget(self.verticalLayoutWidget)
        self.videoWidget.setObjectName(u"videoWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.videoWidget.sizePolicy().hasHeightForWidth())
        self.videoWidget.setSizePolicy(sizePolicy1)
        self.videoWidget.setAcceptDrops(True)

        self.verticalLayout.addWidget(self.videoWidget)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.soundButton = QPushButton(self.verticalLayoutWidget)
        self.soundButton.setObjectName(u"soundButton")
        self.soundButton.setStyleSheet(u"padding: 5px")
        icon = QIcon()
        icon.addFile(u":/icons/speaker.wave.3.fill.on.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addFile(u":/icons/speaker.wave.3.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.soundButton.setIcon(icon)
        self.soundButton.setIconSize(QSize(32, 32))
        self.soundButton.setCheckable(True)
        self.soundButton.setChecked(False)
        self.soundButton.setAutoDefault(False)
        self.soundButton.setFlat(False)

        self.horizontalLayout_2.addWidget(self.soundButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.backwardButton = QPushButton(self.verticalLayoutWidget)
        self.backwardButton.setObjectName(u"backwardButton")
        self.backwardButton.setStyleSheet(u"padding-left: 100px")
        icon1 = QIcon()
        icon1.addFile(u":/icons/backward.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.backwardButton.setIcon(icon1)
        self.backwardButton.setIconSize(QSize(32, 16))
        self.backwardButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.backwardButton)

        self.playPauseButton = QPushButton(self.verticalLayoutWidget)
        self.playPauseButton.setObjectName(u"playPauseButton")
        font1 = QFont()
        font1.setFamilies([u"SF Pro Rounded"])
        font1.setBold(False)
        font1.setItalic(False)
        self.playPauseButton.setFont(font1)
        self.playPauseButton.setAutoFillBackground(False)
        icon2 = QIcon()
        icon2.addFile(u":/icons/custom.play.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon2.addFile(u":/icons/pause.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.playPauseButton.setIcon(icon2)
        self.playPauseButton.setIconSize(QSize(25, 25))
        self.playPauseButton.setCheckable(True)
        self.playPauseButton.setChecked(False)
        self.playPauseButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.playPauseButton)

        self.forwardButton = QPushButton(self.verticalLayoutWidget)
        self.forwardButton.setObjectName(u"forwardButton")
        self.forwardButton.setStyleSheet(u"")
        icon3 = QIcon()
        icon3.addFile(u":/icons/forward.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.forwardButton.setIcon(icon3)
        self.forwardButton.setIconSize(QSize(32, 16))
        self.forwardButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.forwardButton)

        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName(u"label")
        self.label.setPixmap(QPixmap(u"../../.designer/backup/icons/gauge.open.with.lines.needle.33percent.svg"))

        self.horizontalLayout_2.addWidget(self.label)

        self.speedBox = QComboBox(self.verticalLayoutWidget)
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.speedBox.addItem("")
        self.speedBox.setObjectName(u"speedBox")
        self.speedBox.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        self.speedBox.setIconSize(QSize(16, 16))
        self.speedBox.setFrame(True)

        self.horizontalLayout_2.addWidget(self.speedBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.clipButton = QPushButton(self.verticalLayoutWidget)
        self.clipButton.setObjectName(u"clipButton")
        self.clipButton.setEnabled(True)
        font2 = QFont()
        font2.setFamilies([u"SF Pro Text"])
        font2.setPointSize(20)
        font2.setBold(False)
        font2.setItalic(False)
        self.clipButton.setFont(font2)
        self.clipButton.setStyleSheet(u"padding-right: 5px")
        icon4 = QIcon()
        icon4.addFile(u":/icons/record.circle.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon4.addFile(u":/icons/record.circle.action.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.clipButton.setIcon(icon4)
        self.clipButton.setIconSize(QSize(26, 26))
        self.clipButton.setCheckable(True)
        self.clipButton.setChecked(False)
        self.clipButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.clipButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.splitter.addWidget(self.verticalLayoutWidget)

        self.horizontalLayout.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1841, 24))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        font3 = QFont()
        font3.setFamilies([u"SF Pro"])
        font3.setPointSize(14)
        font3.setBold(False)
        font3.setItalic(False)
        self.menuFile.setFont(font3)
        self.menuFile.setTearOffEnabled(False)
        self.menuFile.setSeparatorsCollapsible(False)
        self.menuBearbeiten = QMenu(self.menubar)
        self.menuBearbeiten.setObjectName(u"menuBearbeiten")
        self.menuBearbeiten.setFont(font3)
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuBearbeiten.menuAction())
        self.menuFile.addAction(self.actionLoad_Video)
        self.menuFile.addAction(self.actionAnalyse_laden)
        self.menuFile.addAction(self.actionAnalyse_speichern)
        self.menuFile.addAction(self.actionClips_Exportieren)
        self.menuFile.addAction(self.actionVideo_Exportieren)
        self.menuBearbeiten.addAction(self.actionAnalyse_entfernen)

        self.retranslateUi(MainWindow)

        self.soundButton.setDefault(False)
        self.speedBox.setCurrentIndex(2)
        self.clipButton.setDefault(False)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Video Analyse", None))
        self.actionLoad_Video.setText(QCoreApplication.translate("MainWindow", u"Video laden", None))
#if QT_CONFIG(shortcut)
        self.actionLoad_Video.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionAnalyse_laden.setText(QCoreApplication.translate("MainWindow", u"Analyse laden", None))
#if QT_CONFIG(shortcut)
        self.actionAnalyse_laden.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionAnalyse_speichern.setText(QCoreApplication.translate("MainWindow", u"Analyse speichern", None))
#if QT_CONFIG(shortcut)
        self.actionAnalyse_speichern.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionClips_Exportieren.setText(QCoreApplication.translate("MainWindow", u"Clips Exportieren", None))
#if QT_CONFIG(shortcut)
        self.actionClips_Exportieren.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionAnalyse_entfernen.setText(QCoreApplication.translate("MainWindow", u"Analyse entfernen", None))
        self.actionVideo_Exportieren.setText(QCoreApplication.translate("MainWindow", u"Video Exportieren", None))
#if QT_CONFIG(shortcut)
        self.actionVideo_Exportieren.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+E", None))
#endif // QT_CONFIG(shortcut)
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MainWindow", u"Stop", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Start", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Clip", None));
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"No Video", None))
        self.soundButton.setText("")
#if QT_CONFIG(shortcut)
        self.soundButton.setShortcut(QCoreApplication.translate("MainWindow", u"M", None))
#endif // QT_CONFIG(shortcut)
        self.backwardButton.setText("")
#if QT_CONFIG(shortcut)
        self.backwardButton.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Left", None))
#endif // QT_CONFIG(shortcut)
        self.playPauseButton.setText("")
#if QT_CONFIG(shortcut)
        self.playPauseButton.setShortcut(QCoreApplication.translate("MainWindow", u"Space", None))
#endif // QT_CONFIG(shortcut)
        self.forwardButton.setText("")
#if QT_CONFIG(shortcut)
        self.forwardButton.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Right", None))
#endif // QT_CONFIG(shortcut)
        self.label.setText("")
        self.speedBox.setItemText(0, QCoreApplication.translate("MainWindow", u"0.25x", None))
        self.speedBox.setItemText(1, QCoreApplication.translate("MainWindow", u"0.5x", None))
        self.speedBox.setItemText(2, QCoreApplication.translate("MainWindow", u"1x", None))
        self.speedBox.setItemText(3, QCoreApplication.translate("MainWindow", u"2x", None))

        self.clipButton.setText("")
#if QT_CONFIG(shortcut)
        self.clipButton.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+R", None))
#endif // QT_CONFIG(shortcut)
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"Datei", None))
        self.menuBearbeiten.setTitle(QCoreApplication.translate("MainWindow", u"Bearbeiten", None))
    # retranslateUi

