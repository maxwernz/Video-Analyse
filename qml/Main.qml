// The Qt Quick scene the packaged application proves it can load and render.
//
// It is deliberately the smallest window that exercises the whole path — the
// QML engine, the scene graph, and the graphics backend — so that packaging is
// settled before the workspace is built on top of it. Later stages of the
// migration replace this content; they do not replace this file's role as the
// application's single QML entry point.

import QtQuick

Window {
    id: root

    width: 1280
    height: 720
    minimumWidth: 1200
    minimumHeight: 700
    visible: true
    title: "Video Analyse"
    color: "#131518"

    Text {
        anchors.centerIn: parent
        text: "Video Analyse"
        color: "#E8EAED"
        font.pixelSize: 15
    }
}
