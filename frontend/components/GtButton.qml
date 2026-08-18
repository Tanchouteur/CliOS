import QtQuick
import "../style" as T

Rectangle {
    id: root
    signal clicked()
    property string text: "ACTION"
    property string subtext: ""
    property color accentColor: T.StyleManager.accent
    property bool primary: false
    property bool destructive: false
    implicitWidth: 210
    implicitHeight: 72
    radius: T.StyleManager.radiusSmall
    opacity: enabled ? (touch.pressed ? 0.72 : 1.0) : 0.55
    color: primary ? Qt.darker(accentColor, 1.45) : T.StyleManager.surfaceRaised
    border.width: primary ? 2 : T.StyleManager.borderWidth
    border.color: destructive ? T.StyleManager.danger : (primary ? accentColor : T.StyleManager.outline)
    scale: touch.pressed ? 0.985 : 1.0
    Behavior on opacity { NumberAnimation { duration: T.StyleManager.durationFast } }
    Behavior on scale { NumberAnimation { duration: T.StyleManager.durationFast } }

    Column {
        anchors.centerIn: parent
        spacing: 3
        width: parent.width - 24
        Text {
            width: parent.width
            text: root.text
            color: root.destructive ? T.StyleManager.danger : T.StyleManager.text
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 19
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        Text {
            visible: root.subtext !== ""
            width: parent.width
            text: root.subtext
            color: root.primary ? T.StyleManager.text : T.StyleManager.textSecondary
            opacity: 0.82
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: touch
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
