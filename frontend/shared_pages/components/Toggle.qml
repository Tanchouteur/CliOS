import QtQuick
import "../../style" as T

Rectangle {
    id: root
    signal toggled(bool checked)
    property bool checked: false
    implicitWidth: 64
    implicitHeight: 36
    radius: height / 2
    opacity: enabled ? 1.0 : 0.35
    color: checked ? T.StyleManager.accent : T.StyleManager.surfaceSoft
    border.width: 1
    border.color: checked ? T.StyleManager.accent : T.StyleManager.outline

    Rectangle {
        width: 28
        height: 28
        radius: 14
        y: 4
        x: root.checked ? root.width - width - 4 : 4
        color: root.checked ? T.StyleManager.background : T.StyleManager.text
        Behavior on x { NumberAnimation { duration: T.StyleManager.durationNormal; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.toggled(!root.checked)
    }
}
