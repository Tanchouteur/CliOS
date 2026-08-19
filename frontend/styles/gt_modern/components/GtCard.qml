import QtQuick
import "../../../style" as T

Rectangle {
    id: root
    property string title: ""
    property color accentColor: T.StyleManager.accent
    property bool highlighted: false
    property alias content: contentItem.data
    default property alias cardData: contentItem.data

    color: highlighted ? T.StyleManager.surfaceRaised : T.StyleManager.surface
    radius: T.StyleManager.radiusMedium
    border.width: T.StyleManager.borderWidth
    border.color: highlighted ? accentColor : T.StyleManager.outline

    Text {
        id: titleText
        visible: root.title !== ""
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 18
        anchors.topMargin: 14
        text: root.title.toUpperCase()
        color: T.StyleManager.textSecondary
        font.family: T.StyleManager.fontFamily
        font.pixelSize: 17
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
    }

    Item {
        id: contentItem
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: root.title !== "" ? titleText.bottom : parent.top
        anchors.margins: 16
        anchors.topMargin: root.title !== "" ? 10 : 16
    }
}
