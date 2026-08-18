import QtQuick
import "../../../style" as T

// Navigation tactile 3 onglets avec effet 3D enfoncé et retour tactile haute réactivité
Item {
    id: root
    width: parent.width
    height: 56

    property string current: "drive"
    signal tabSelected(string tabId)

    readonly property var tabs: [
        { id: "drive", label: "CONDUITE",   icon: "◈" },
        { id: "perf",  label: "PERF",        icon: "⚡" },
        { id: "menu",  label: "MENU",        icon: "☰" }
    ]

    // Fond de la barre de navigation
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.05, 0.09, 0.96)

        // Ligne de biseau supérieure
        Rectangle {
            anchors.top: parent.top
            width: parent.width; height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 200
        anchors.rightMargin: 200

        Repeater {
            model: root.tabs
            delegate: Item {
                width: parent.width / root.tabs.length
                height: root.height

                readonly property bool isActive: root.current === modelData.id

                Rectangle {
                    id: btnBg
                    anchors.fill: parent
                    anchors.margins: 4
                    radius: T.StyleManager.radiusSmall
                    color: isActive
                        ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.16)
                        : (touchArea.pressed ? Qt.rgba(1, 1, 1, 0.06) : "transparent")
                    border.width: isActive ? 1 : 0
                    border.color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.6)

                    Behavior on color { ColorAnimation { duration: 180 } }

                    // Ligne néon active en bas
                    Rectangle {
                        visible: isActive
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 3
                        radius: 1.5
                        color: T.StyleManager.accent
                    }

                    // Lueur d'ambiance sur l'onglet actif
                    Rectangle {
                        visible: isActive
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * 0.7
                        height: 6
                        radius: 3
                        color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.45)
                    }
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 8
                    scale: touchArea.pressed ? 0.95 : 1.0
                    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }

                    Text {
                        text: modelData.icon
                        color: isActive ? T.StyleManager.accent : Qt.rgba(1, 1, 1, 0.40)
                        font.pixelSize: 15
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: modelData.label
                        color: isActive ? "#FFFFFF" : Qt.rgba(1, 1, 1, 0.50)
                        font.pixelSize: isActive ? 15 : 14
                        font.weight: isActive ? Font.Black : Font.Bold
                        font.letterSpacing: 2.0
                        anchors.verticalCenter: parent.verticalCenter

                        Behavior on color { ColorAnimation { duration: 180 } }
                    }
                }

                // Zone tactile complète
                MouseArea {
                    id: touchArea
                    anchors.fill: parent
                    onClicked: root.tabSelected(modelData.id)
                }
            }
        }
    }
}
