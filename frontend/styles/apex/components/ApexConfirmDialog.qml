import QtQuick
import QtQuick.Layouts
import "../../../style" as T

// Dialogue de confirmation universel Apex
Item {
    id: root

    signal accepted()
    signal rejected()

    property string title:      "Confirmer"
    property string message:    ""
    property string acceptText: "CONFIRMER"
    property bool   dangerous:  false

    anchors.fill: parent
    visible: opacity > 0.01
    opacity: 0.0

    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    function open()  { opacity = 1.0 }
    function close() { opacity = 0.0 }

    // Overlay sombre
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.01, 0.02, 0.05, 0.92)
        MouseArea { anchors.fill: parent; onClicked: root.rejected() }
    }

    // Carte centrale
    Rectangle {
        anchors.centerIn: parent
        width: 560; height: 300
        radius: T.StyleManager.radiusLarge
        color: "#0E1828"
        border.width: 1
        border.color: root.dangerous
            ? Qt.rgba(1.0, 0.2, 0.1, 0.5)
            : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.4)

        // Ligne supérieure colorée
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2; radius: parent.radius
            color: root.dangerous ? "#FF1744" : T.StyleManager.accent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 32
            spacing: 18

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.title
                color: "#FFFFFF"
                font.pixelSize: 22
                font.weight: Font.Black
                font.letterSpacing: 1.5
            }

            Text {
                Layout.fillWidth: true
                text: root.message
                color: Qt.rgba(1, 1, 1, 0.55)
                font.pixelSize: 16
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                // Annuler
                Rectangle {
                    Layout.fillWidth: true; height: 52; radius: T.StyleManager.radiusMedium
                    color: Qt.rgba(1, 1, 1, 0.06)
                    border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.12)
                    Text {
                        anchors.centerIn: parent; text: "ANNULER"
                        color: Qt.rgba(1, 1, 1, 0.5)
                        font.pixelSize: 14; font.weight: Font.Bold; font.letterSpacing: 2
                    }
                    MouseArea {
                        anchors.fill: parent
                        onPressed:  parent.opacity = 0.7
                        onReleased: parent.opacity = 1.0
                        onClicked:  root.rejected()
                    }
                }

                // Confirmer
                Rectangle {
                    Layout.fillWidth: true; height: 52; radius: T.StyleManager.radiusMedium
                    color: root.dangerous
                        ? Qt.rgba(1.0, 0.1, 0.1, 0.18)
                        : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.18)
                    border.width: 1
                    border.color: root.dangerous ? "#FF1744" : T.StyleManager.accent
                    Text {
                        anchors.centerIn: parent; text: root.acceptText
                        color: root.dangerous ? "#FF4444" : T.StyleManager.accent
                        font.pixelSize: 14; font.weight: Font.Bold; font.letterSpacing: 2
                    }
                    MouseArea {
                        anchors.fill: parent
                        onPressed:  parent.opacity = 0.7
                        onReleased: parent.opacity = 1.0
                        onClicked:  root.accepted()
                    }
                }
            }
        }
    }
}
