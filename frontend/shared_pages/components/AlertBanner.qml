import QtQuick
import "../../style" as T

Rectangle {
    id: root
    property string message: ""
    property string level: "warning"
    property bool shown: false
    signal dismissed()
    width: 760
    height: 58
    radius: T.StyleManager.radiusSmall
    color: level === "danger" ? Qt.darker(T.StyleManager.danger, 1.6)
                              : Qt.darker(T.StyleManager.warning, 1.75)
    border.width: 2
    border.color: level === "danger" ? T.StyleManager.danger : T.StyleManager.warning
    opacity: shown ? 1 : 0
    y: shown ? 68 : 44
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: T.StyleManager.durationNormal } }
    Behavior on y { NumberAnimation { duration: T.StyleManager.durationNormal; easing.type: Easing.OutCubic } }

    Text {
        anchors.centerIn: parent
        text: root.message
        color: T.StyleManager.text
        font.family: T.StyleManager.fontFamily
        font.pixelSize: 20
        font.weight: Font.Bold
    }
}
