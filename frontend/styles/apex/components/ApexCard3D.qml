import QtQuick
import "../../../style" as T

// Surface tactile en aluminium noir : relief net, sans ombre floue coûteuse.
Item {
    id: root
    property string title: ""
    property bool highlighted: false
    property color glowColor: T.StyleManager.accent
    default property alias contentData: contentItem.data

    transform: Translate { y: root.entered ? 0 : 8 }
    opacity: entered ? 1.0 : 0.0
    property bool entered: false
    Component.onCompleted: entered = true
    Behavior on opacity { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 9
        anchors.leftMargin: 7
        anchors.rightMargin: 7
        radius: 24
        color: "#8F000000"
    }

    Rectangle {
        id: body
        anchors.fill: parent
        radius: 22
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: root.highlighted ? "#14232D" : "#111A25" }
            GradientStop { position: 0.08; color: "#0B111A" }
            GradientStop { position: 1.0; color: "#070B11" }
        }
        border.width: 1
        border.color: root.highlighted
            ? Qt.rgba(root.glowColor.r, root.glowColor.g, root.glowColor.b, 0.82)
            : "#26394B"

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 22
            anchors.rightMargin: 22
            height: 1
            color: root.highlighted ? root.glowColor : "#4FFFFFFF"
        }

        Rectangle {
            visible: root.highlighted
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: Math.min(parent.height * 0.52, 120)
            radius: 2
            color: root.glowColor
        }
    }

    Row {
        id: header
        visible: root.title !== ""
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 18
        anchors.topMargin: 15
        spacing: 9

        Rectangle {
            width: 18
            height: 3
            radius: 2
            color: root.highlighted ? root.glowColor : T.StyleManager.accent
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.title
            color: "#C2D0DC"
            font.pixelSize: 12
            font.weight: Font.Bold
            font.letterSpacing: 1.8
        }
    }

    Item {
        id: contentItem
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: root.title !== "" ? header.bottom : parent.top
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.bottomMargin: 16
        anchors.topMargin: root.title !== "" ? 13 : 16
    }
}
