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
    QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QProgressBar, QPushButton, QSizePolicy, QSlider,
    QSpacerItem, QSplitter, QStackedWidget, QTabWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

from clip_handler import (CreateClip, EditClip)
from treewidget import TreeWidget
from video_thumbnail_widget import VideoThumbnailWidget
from videowidget import VideoWidget
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setWindowModality(Qt.NonModal)
        MainWindow.resize(1840, 1106)
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(False)
        font.setItalic(False)
        MainWindow.setFont(font)
        MainWindow.setAcceptDrops(True)
        MainWindow.setStyleSheet(u"background-color: rgb(31, 31, 31);\n"
"color: rgb(255, 255, 255);")
        MainWindow.setTabShape(QTabWidget.Rounded)
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
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMouseTracking(True)
        self.centralwidget.setStyleSheet(u"QPushButton{\n"
"border: none;\n"
"}")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setStyleSheet(u"QSplitter::handle {\n"
"    background-color: rgb(20, 20, 20);  /* Color of the border/handle */\n"
"    width: 1px;  /* Width of the border for vertical splitter */\n"
"    height: 1px; /* Height of the border for horizontal splitter */\n"
"}\n"
"\n"
"/* Optional: Add hover effect */\n"
"QSplitter::handle:hover {\n"
"    background-color: rgb(40, 40, 40);  /* Slightly lighter when hovering */\n"
"}\n"
"\n"
"/* If you want to style horizontal and vertical handles differently */\n"
"QSplitter::handle:horizontal {\n"
"    width: 1px;\n"
"}\n"
"\n"
"QSplitter::handle:vertical {\n"
"    height: 1px;\n"
"}")
        self.splitter.setOrientation(Qt.Horizontal)
        self.tabWidget = QTabWidget(self.splitter)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setStyleSheet(u"/* Style the tab using the tab sub-control. Note that\n"
"    it reads QTabBar _not_ QTabWidget */\n"
"QTabBar::tab {\n"
"    background: rgb(31, 31, 31);\n"
"    /*border: 2px solid #C4C4C3;*/\n"
"	padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	padding-top: 1px;\n"
"	padding-bottom: 1px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"	background: rgb(55, 55, 55);\n"
"	border-radius: 3\n"
"}\n"
"\n"
"\n"
"QTabWidget::tab-bar {\n"
"	border: 1px solid rgb(20, 20, 20);\n"
"}")
        self.tabWidget.setTabShape(QTabWidget.Rounded)
        self.tabWidget.setElideMode(Qt.ElideRight)
        self.tabWidget.setUsesScrollButtons(False)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setTabBarAutoHide(False)
        self.videoTab = QWidget()
        self.videoTab.setObjectName(u"videoTab")
        self.verticalLayout_2 = QVBoxLayout(self.videoTab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.videoStack = QStackedWidget(self.videoTab)
        self.videoStack.setObjectName(u"videoStack")
        self.videosPage = QWidget()
        self.videosPage.setObjectName(u"videosPage")
        self.verticalLayout_5 = QVBoxLayout(self.videosPage)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.videoThumbnailsWidget = VideoThumbnailWidget(self.videosPage)
        self.videoThumbnailsWidget.setObjectName(u"videoThumbnailsWidget")

        self.verticalLayout_5.addWidget(self.videoThumbnailsWidget)

        self.videoStack.addWidget(self.videosPage)
        self.loadPage = QWidget()
        self.loadPage.setObjectName(u"loadPage")
        sizePolicy.setHeightForWidth(self.loadPage.sizePolicy().hasHeightForWidth())
        self.loadPage.setSizePolicy(sizePolicy)
        self.verticalLayout_4 = QVBoxLayout(self.loadPage)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer = QSpacerItem(20, 434, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.loadVideoButton = QPushButton(self.loadPage)
        self.loadVideoButton.setObjectName(u"loadVideoButton")
        self.loadVideoButton.setMinimumSize(QSize(80, 80))
        self.loadVideoButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #333333;\n"
"    border-radius: 8px;\n"
"    max-width: 80px;\n"
"    max-height: 80px;\n"
"	border-radius: 10px;\n"
"}\n"
"\n"
"QPushButton::pressed {\n"
"	background-color: rgb(35, 35, 35)\n"
"}")
        icon = QIcon()
        icon.addFile(u":/icons/arrow.down@5x.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.loadVideoButton.setIcon(icon)
        self.loadVideoButton.setIconSize(QSize(50, 50))

        self.horizontalLayout_5.addWidget(self.loadVideoButton)


        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.verticalSpacer_2 = QSpacerItem(20, 434, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)

        self.videoStack.addWidget(self.loadPage)

        self.verticalLayout_2.addWidget(self.videoStack)

        self.tabWidget.addTab(self.videoTab, "")
        self.clipTab = QWidget()
        self.clipTab.setObjectName(u"clipTab")
        sizePolicy.setHeightForWidth(self.clipTab.sizePolicy().hasHeightForWidth())
        self.clipTab.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.clipTab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.treeWidget = TreeWidget(self.clipTab)
        self.treeWidget.setObjectName(u"treeWidget")
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMinimumSize(QSize(0, 0))
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(16)
        font1.setBold(False)
        font1.setItalic(False)
        self.treeWidget.setFont(font1)
        self.treeWidget.setAcceptDrops(True)
        self.treeWidget.setStyleSheet(u"QTreeView {\n"
"	background-color: rgb(55, 55, 55);\n"
"	gridline-color: rgb(255, 126, 227);\n"
"	border-color: rgb(40, 40, 40);\n"
"	border-radius: 10px;\n"
"}\n"
"\n"
"QTreeView::header {\n"
"	min-height: 30px;\n"
"}\n"
"\n"
"QHeaderView {\n"
"	min-height: 30px;\n"
"	border-right: 1px solid rgb(40, 40, 40);\n"
"	border-bottom: 1px solid rgb(40, 40, 40);\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"    background-color: rgb(55, 55, 55);\n"
"    color: rgb(255, 255, 255);\n"
"	border-top: none;\n"
"	border-right: 1px solid rgb(40, 40, 40);\n"
"	border-bottom: 1px solid rgb(40, 40, 40);\n"
"	gridline-color: rgb(255, 255, 255);\n"
"    text-align: center;\n"
"	min-height: 30px;\n"
"	font: 15px;\n"
"	padding-left: 5px;\n"
"}\n"
"\n"
"QHeaderView::section:first {\n"
"	border-top-left-radius: 10px;\n"
"}\n"
"\n"
"QHeaderView::section:last {\n"
"	border-right: none;\n"
"	border-top-right-radius: 10px;\n"
"}\n"
"\n"
"QHeaderView::down-arrow {\n"
"	image: url(:/icons/chevron.compact.down.png);\n"
"	width: 16px;\n"
"	heig"
                        "ht: 10px;\n"
"	padding: 5px;\n"
"}\n"
"\n"
"QHeaderView::up-arrow {\n"
"	image: url(:/icons/chevron.compact.up.png);\n"
"	width: 16px;\n"
"	height: 10px;\n"
"	padding: 5px;\n"
"}\n"
"\n"
"QTreeView::branch:has-children:!has-siblings:closed,\n"
"QTreeView::branch:closed:has-children:has-siblings {\n"
"        border-image: none;\n"
"	image: url(:/icons/chevron.right.png);\n"
"	padding: 2px;\n"
"}\n"
"\n"
"QTreeView::branch:open:has-children:!has-siblings,\n"
"QTreeView::branch:open:has-children:has-siblings  {\n"
"        border-image: none;\n"
"	image: url(:/icons/chevron.down.png);\n"
"}\n"
"\n"
"QTreeView::item {\n"
"    background-color: transparent;\n"
"    border: none;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QTreeView::item:hover {\n"
"    background-color: rgb(65, 65, 65);\n"
"}\n"
"\n"
"QTreeView::item:selected {\n"
"    background-color: rgb(100, 100, 100);\n"
"    color: white; \n"
"}\n"
"\n"
"QTreeView::branch:selected {\n"
"	background-color: rgb(100,100,100);\n"
"}\n"
"")
        self.treeWidget.setFrameShape(QFrame.StyledPanel)
        self.treeWidget.setFrameShadow(QFrame.Plain)
        self.treeWidget.setLineWidth(4)
        self.treeWidget.setMidLineWidth(1)
        self.treeWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.treeWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.header().setVisible(False)
        self.treeWidget.header().setCascadingSectionResizes(False)
        self.treeWidget.header().setMinimumSectionSize(100)
        self.treeWidget.header().setHighlightSections(False)

        self.verticalLayout_3.addWidget(self.treeWidget)

        self.clipHandler = CreateClip(self.clipTab)
        self.clipHandler.setObjectName(u"clipHandler")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.clipHandler.sizePolicy().hasHeightForWidth())
        self.clipHandler.setSizePolicy(sizePolicy1)
        self.clipHandler.setMinimumSize(QSize(0, 100))

        self.verticalLayout_3.addWidget(self.clipHandler)

        self.editHandler = EditClip(self.clipTab)
        self.editHandler.setObjectName(u"editHandler")
        self.editHandler.setMinimumSize(QSize(0, 100))

        self.verticalLayout_3.addWidget(self.editHandler)

        self.tabWidget.addTab(self.clipTab, "")
        self.splitter.addWidget(self.tabWidget)
        self.verticalLayoutWidget = QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.titleLabel = QLabel(self.verticalLayoutWidget)
        self.titleLabel.setObjectName(u"titleLabel")
        font2 = QFont()
        font2.setFamilies([u"Arial"])
        font2.setPointSize(24)
        font2.setBold(False)
        font2.setItalic(False)
        self.titleLabel.setFont(font2)
        self.titleLabel.setStyleSheet(u"")
        self.titleLabel.setIndent(10)

        self.horizontalLayout_4.addWidget(self.titleLabel)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)

        self.exportLayout = QHBoxLayout()
        self.exportLayout.setSpacing(4)
        self.exportLayout.setObjectName(u"exportLayout")
        self.exportFinishedLabel = QLabel(self.verticalLayoutWidget)
        self.exportFinishedLabel.setObjectName(u"exportFinishedLabel")
        font3 = QFont()
        font3.setFamilies([u"Arial"])
        font3.setPointSize(16)
        self.exportFinishedLabel.setFont(font3)

        self.exportLayout.addWidget(self.exportFinishedLabel)

        self.openExportButton = QPushButton(self.verticalLayoutWidget)
        self.openExportButton.setObjectName(u"openExportButton")
        font4 = QFont()
        font4.setFamilies([u"Arial"])
        font4.setPointSize(16)
        font4.setBold(True)
        self.openExportButton.setFont(font4)
        self.openExportButton.setStyleSheet(u"QPushButton:hover {\n"
"	text-decoration: underline;\n"
"}")

        self.exportLayout.addWidget(self.openExportButton)


        self.horizontalLayout_4.addLayout(self.exportLayout)

        self.progressBar = QProgressBar(self.verticalLayoutWidget)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setStyleSheet(u"QProgressBar {\n"
"		border: 2px solid rgb(255, 255, 255);\n"
"        border-radius: 7px;\n"
"        background-color: rgb(55, 55, 55);\n"
"        height: 18px;\n"
"		max-width: 80px;\n"
"		text-align: center;\n"
"        font: bold 13px;\n"
"        color: rgb(130, 130, 130);\n"
"		margin-right: 15px;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"        background-color: rgb(255, 255, 255);\n"
"        /*border-radius: 9px;*/\n"
"\n"
"}\n"
"")
        self.progressBar.setValue(0)
        self.progressBar.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.progressBar.setTextVisible(True)
        self.progressBar.setTextDirection(QProgressBar.BottomToTop)

        self.horizontalLayout_4.addWidget(self.progressBar)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.widget = QWidget(self.verticalLayoutWidget)
        self.widget.setObjectName(u"widget")
        self.widget.setStyleSheet(u"border-top: 1px solid rgb(20, 20, 20);\n"
"min-height: 1px;")

        self.verticalLayout.addWidget(self.widget)

        self.videoWidget = VideoWidget(self.verticalLayoutWidget)
        self.videoWidget.setObjectName(u"videoWidget")
        sizePolicy.setHeightForWidth(self.videoWidget.sizePolicy().hasHeightForWidth())
        self.videoWidget.setSizePolicy(sizePolicy)
        self.videoWidget.setMinimumSize(QSize(900, 600))
        self.videoWidget.setMaximumSize(QSize(16777215, 16777215))
        self.videoWidget.setAcceptDrops(True)
        self.videoWidget.setStyleSheet(u"border: 1px solid rgb(55, 55, 55);\n"
"margin: 50px;")

        self.verticalLayout.addWidget(self.videoWidget)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.position_label = QLabel(self.verticalLayoutWidget)
        self.position_label.setObjectName(u"position_label")
        self.position_label.setMinimumSize(QSize(70, 0))
        self.position_label.setMaximumSize(QSize(80, 16777215))
        font5 = QFont()
        font5.setFamilies([u"Arial"])
        font5.setPointSize(20)
        font5.setBold(False)
        font5.setItalic(False)
        self.position_label.setFont(font5)
        self.position_label.setStyleSheet(u"QLabels {\n"
"font: 15px \"SF Pro\";\n"
"}")

        self.horizontalLayout_3.addWidget(self.position_label)

        self.label_3 = QLabel(self.verticalLayoutWidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font5)

        self.horizontalLayout_3.addWidget(self.label_3)

        self.duration_label = QLabel(self.verticalLayoutWidget)
        self.duration_label.setObjectName(u"duration_label")
        self.duration_label.setMinimumSize(QSize(70, 0))
        self.duration_label.setMaximumSize(QSize(80, 16777215))
        self.duration_label.setFont(font5)

        self.horizontalLayout_3.addWidget(self.duration_label)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_4)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.position_slider = QSlider(self.verticalLayoutWidget)
        self.position_slider.setObjectName(u"position_slider")
        self.position_slider.setStyleSheet(u"QSlider {\n"
"    background: transparent;  /* Transparent background for the slider */\n"
"    padding: 5px;         /* Adds some space around the slider */\n"
"}\n"
"\n"
"\n"
"QSlider::groove:horizontal {\n"
"    border: 1px solid rgb(70, 70, 70);   /* Subtle border for the groove */\n"
"    height: 8px;                        /* Increased thickness for the groove */\n"
"	background-color: rgb(55, 55, 55);\n"
"    border-radius: 4px;                 /* Rounded edges for the groove */\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: rgb(255, 255, 255);     /* White handle for a clean contrast */\n"
"	border: 2px solid rgb(255, 255, 255);\n"
"    width: 12px;                        /* Handle width */\n"
"    height: 12px;                       /* Handle height */\n"
"    border-radius: 7px;                 /* Fully rounded handle */\n"
"    margin: -4px 0px;                   /* Adjusts handle positioning relative to the groove */\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    border:"
                        " 2px solid rgb(65, 65, 65);\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"	background-color: rgb(81, 113, 186);\n"
"    border-radius: 4px;                 /* Rounded edges for the filled section */\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background: rgb(55, 55, 55);        /* Same color as the groove for the unfilled portion */\n"
"    border-radius: 4px;                 /* Rounded edges for the unfilled section */\n"
"}\n"
"\n"
"")
        self.position_slider.setSliderPosition(0)
        self.position_slider.setOrientation(Qt.Horizontal)

        self.verticalLayout.addWidget(self.position_slider)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.soundButton = QPushButton(self.verticalLayoutWidget)
        self.soundButton.setObjectName(u"soundButton")
        self.soundButton.setStyleSheet(u"padding: 5px")
        icon1 = QIcon()
        icon1.addFile(u":/icons/speaker.wave.3.fill.on.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon1.addFile(u":/icons/speaker.wave.3.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.soundButton.setIcon(icon1)
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/backward.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.backwardButton.setIcon(icon2)
        self.backwardButton.setIconSize(QSize(32, 16))
        self.backwardButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.backwardButton)

        self.playPauseButton = QPushButton(self.verticalLayoutWidget)
        self.playPauseButton.setObjectName(u"playPauseButton")
        font6 = QFont()
        font6.setFamilies([u"SF Pro Rounded"])
        font6.setBold(False)
        font6.setItalic(False)
        self.playPauseButton.setFont(font6)
        self.playPauseButton.setAutoFillBackground(False)
        icon3 = QIcon()
        icon3.addFile(u":/icons/custom.play.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon3.addFile(u":/icons/pause.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.playPauseButton.setIcon(icon3)
        self.playPauseButton.setIconSize(QSize(25, 25))
        self.playPauseButton.setCheckable(True)
        self.playPauseButton.setChecked(False)
        self.playPauseButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.playPauseButton)

        self.forwardButton = QPushButton(self.verticalLayoutWidget)
        self.forwardButton.setObjectName(u"forwardButton")
        self.forwardButton.setStyleSheet(u"")
        icon4 = QIcon()
        icon4.addFile(u":/icons/forward.fill.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.forwardButton.setIcon(icon4)
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
        self.speedBox.setStyleSheet(u"QComboBox {\n"
"    border: 2px solid rgb(31, 31, 31); /* Light gray border */\n"
"    border-radius: 5px;\n"
"    padding: 5px;              /* Padding inside the combo box */\n"
"    background-color: rgb(31, 31, 31);\n"
"    font: 14px;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    border: none;\n"
"    width: 30px;                    /* Width of the drop-down button */\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    image: url(:/icons/gauge.with.needle.fill.png);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    background-color: rgb(31, 31, 31); /* Black background for the drop-down */\n"
"    selection-background-color: rgb(255, 0, 0); /* Red background for selected item */\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView::item {\n"
"    background-color: rgb(31, 31, 31); /* Default background for items */\n"
"    color: white;                      /* White text for items */\n"
"}\n"
"\n"
"QComboBox QAbstractItemView::item"
                        ":hover {\n"
"    background-color: rgb(66, 65, 64); /* Same hover background as !editable:on */\n"
"    color: white;                      /* White text on hover */\n"
"}\n"
"\n"
"QComboBox::hover {\n"
"    border: 2px solid rgb(65, 65, 65); /* Light blue border on hover */\n"
"}\n"
"\n"
"/* QComboBox gets the \"on\" state when the popup is open */\n"
"QComboBox:!editable:on, QComboBox::drop-down:editable:on {\n"
"    background-color: rgb(66, 65, 64);  /* Background for when popup is open */\n"
"}\n"
"")
        self.speedBox.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        self.speedBox.setIconSize(QSize(16, 16))
        self.speedBox.setFrame(True)

        self.horizontalLayout_2.addWidget(self.speedBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.clipButton = QPushButton(self.verticalLayoutWidget)
        self.clipButton.setObjectName(u"clipButton")
        self.clipButton.setEnabled(True)
        font7 = QFont()
        font7.setFamilies([u"SF Pro Text"])
        font7.setPointSize(20)
        font7.setBold(False)
        font7.setItalic(False)
        self.clipButton.setFont(font7)
        self.clipButton.setStyleSheet(u"padding-right: 5px")
        icon5 = QIcon()
        icon5.addFile(u":/icons/record.circle.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon5.addFile(u":/icons/record.circle.action.png", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.clipButton.setIcon(icon5)
        self.clipButton.setIconSize(QSize(26, 26))
        self.clipButton.setCheckable(True)
        self.clipButton.setChecked(False)
        self.clipButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.clipButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.splitter.addWidget(self.verticalLayoutWidget)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1840, 24))
        self.menubar.setFont(font)
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        font8 = QFont()
        font8.setFamilies([u"SF Pro"])
        font8.setPointSize(14)
        font8.setBold(False)
        font8.setItalic(False)
        self.menuFile.setFont(font8)
        self.menuFile.setTearOffEnabled(False)
        self.menuFile.setSeparatorsCollapsible(False)
        self.menuBearbeiten = QMenu(self.menubar)
        self.menuBearbeiten.setObjectName(u"menuBearbeiten")
        self.menuBearbeiten.setFont(font8)
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuBearbeiten.menuAction())
        self.menuFile.addAction(self.actionLoad_Video)
        self.menuFile.addAction(self.actionAnalyse_laden)
        self.menuFile.addAction(self.actionAnalyse_speichern)
        self.menuFile.addAction(self.actionClips_Exportieren)
        self.menuFile.addAction(self.actionVideo_Exportieren)
        self.menuBearbeiten.addAction(self.actionAnalyse_entfernen)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)
        self.videoStack.setCurrentIndex(0)
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
        self.loadVideoButton.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.videoTab), QCoreApplication.translate("MainWindow", u"Videos", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MainWindow", u"Stop", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Start", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Clip", None));
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.clipTab), QCoreApplication.translate("MainWindow", u"Clips", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"No Video", None))
        self.exportFinishedLabel.setText(QCoreApplication.translate("MainWindow", u"Export erfolgreich", None))
        self.openExportButton.setText(QCoreApplication.translate("MainWindow", u"\u00d6ffnen", None))
        self.position_label.setText(QCoreApplication.translate("MainWindow", u"00:00:00", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"/", None))
        self.duration_label.setText(QCoreApplication.translate("MainWindow", u"00:00:00", None))
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

