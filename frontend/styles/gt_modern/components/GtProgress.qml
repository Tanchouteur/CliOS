import QtQuick
import "../../../style" as T

Item {
    id: root
    property real value: 0
    property real from: 0
    property real to: 100
    property color fillColor: T.StyleManager.accent
    readonly property real ratio: Math.max(0, Math.min(1, (value - from) / Math.max(0.001, to - from)))
    implicitHeight: 10

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: T.StyleManager.gaugeTrack
    }
    Rectangle {
        width: parent.width * root.ratio
        height: parent.height
        radius: height / 2
        color: root.fillColor
        Behavior on width { NumberAnimation { duration: T.StyleManager.durationFast; easing.type: Easing.OutCubic } }
    }
}
