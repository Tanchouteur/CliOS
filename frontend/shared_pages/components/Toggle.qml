import QtQuick
import "../../style" as T

Item {
    id: root
    signal toggled(bool checked)
    property bool checked: false
    // La cible reste tactile (84×56), le commutateur conserve son gabarit compact.
    property bool visualChecked: checked
    implicitWidth: 84
    implicitHeight: 56
    opacity: enabled ? 1.0 : 0.35

    onCheckedChanged: visualChecked = checked

    Rectangle {
        id: track
        anchors.centerIn: parent
        width: 64
        height: 36
        radius: height / 2
        color: root.visualChecked ? T.StyleManager.accent : T.StyleManager.surfaceSoft
        border.width: 1
        border.color: root.visualChecked ? T.StyleManager.accent : T.StyleManager.outline

        Rectangle {
            width: 28
            height: 28
            radius: 14
            y: 4
            x: root.visualChecked ? track.width - width - 4 : 4
            color: root.visualChecked ? T.StyleManager.background : T.StyleManager.text
            Behavior on x { NumberAnimation { duration: T.StyleManager.durationNormal; easing.type: Easing.OutCubic } }
        }
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
