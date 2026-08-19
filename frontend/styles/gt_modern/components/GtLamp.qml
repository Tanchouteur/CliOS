import QtQuick
import "../../../style" as T

Rectangle {
    id: root
    property string code: "ABS"
    property string label: code
    property bool active: false
    property bool blinking: false
    property color lampColor: T.StyleManager.warning

    width: 62
    height: 34
    radius: T.StyleManager.radiusSmall
    color: active ? Qt.rgba(lampColor.r, lampColor.g, lampColor.b, 0.16) : "transparent"
    border.width: 1
    border.color: active ? lampColor : T.StyleManager.outline
    opacity: active ? 1.0 : 0.55

    SequentialAnimation on opacity {
        running: root.active && root.blinking
        loops: Animation.Infinite
        NumberAnimation { to: 0.28; duration: 420 }
        NumberAnimation { to: 1.0; duration: 420 }
    }

    Text {
        anchors.centerIn: parent
        text: root.code
        color: root.active ? root.lampColor : T.StyleManager.textSecondary
        font.family: T.StyleManager.fontFamily
        font.pixelSize: root.code.length > 4 ? 10 : 12
        font.weight: Font.Bold
    }
}
