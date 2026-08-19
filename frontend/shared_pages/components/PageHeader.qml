import QtQuick
import "../../style" as T

Item {
    id: root
    signal backClicked()
    property string title: "PAGE"
    property string subtitle: ""
    property bool showBack: true
    implicitHeight: 64

    Rectangle {
        id: back
        visible: root.showBack
        width: 148
        height: 56
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        radius: T.StyleManager.radiusSmall
        color: backArea.pressed ? T.StyleManager.accentSoft : T.StyleManager.surfaceRaised
        border.width: 1
        border.color: T.StyleManager.outline

        Text {
            anchors.centerIn: parent
            text: "‹  RETOUR"
            color: T.StyleManager.text
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 18
            font.weight: Font.DemiBold
        }
        MouseArea { id: backArea; anchors.fill: parent; onClicked: root.backClicked() }
    }

    Column {
        anchors.left: root.showBack ? back.right : parent.left
        anchors.leftMargin: root.showBack ? 20 : 0
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            text: root.title
            color: T.StyleManager.text
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 27
            font.weight: Font.DemiBold
        }
        Text {
            visible: root.subtitle !== ""
            text: root.subtitle
            color: T.StyleManager.textSecondary
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 15
        }
    }
}
