import QtQuick
import "../../style" as T

Rectangle {
    id: root
    signal toggled(bool checked)
    property bool checked: false
    // Retour immédiat au toucher, puis resynchronisation avec le backend.
    property bool visualChecked: checked
    implicitWidth: 84
    implicitHeight: 56
    radius: height / 2
    opacity: enabled ? 1.0 : 0.35
    color: visualChecked ? T.StyleManager.accent : T.StyleManager.surfaceSoft
    border.width: 1
    border.color: visualChecked ? T.StyleManager.accent : T.StyleManager.outline

    onCheckedChanged: visualChecked = checked

    Rectangle {
        width: 40
        height: 40
        radius: 20
        y: 8
        x: root.visualChecked ? root.width - width - 8 : 8
        color: root.visualChecked ? T.StyleManager.background : T.StyleManager.text
        Behavior on x { NumberAnimation { duration: T.StyleManager.durationNormal; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        onClicked: {
            const nextValue = !root.visualChecked
            root.visualChecked = nextValue
            root.toggled(nextValue)
        }
    }
}
