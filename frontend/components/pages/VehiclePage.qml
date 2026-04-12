import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../style" as T

Item {
    id: vehicleMenuPage

    // Modèle des sous-options du menu Véhicule
    readonly property var menuItems: [
        { label: "Profils & Véhicules", desc: "Changer de voiture ou créer un nouveau profil", icon: "🚗", source: "VehicleProfiles.qml" },
        { label: "Coûts & Statistiques", desc: "Prix du carburant et suivi de maintenance", icon: "⛽", source: "VehicleStats.qml" }
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // --- HEADER ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            Rectangle {
                width: 40; height: 40; radius: 20
                color: backMouse.pressed ? T.Theme.main : (backMouse.containsMouse ? T.Theme.main : T.Theme.bgDimmed)
                border.color: Qt.rgba(1, 1, 1, 0.1)
                border.width: 1

                Text {
                    text: "〈"
                    color: backMouse.pressed || backMouse.containsMouse ? T.Theme.bgMain : T.Theme.textMain
                    font.pixelSize: 20; font.bold: true
                    anchors.centerIn: parent
                    transform: Translate { x: -2 }
                }

                MouseArea {
                    id: backMouse
                    anchors.fill: parent
                    hoverEnabled: true // Gardé pour les tests sur PC, inoffensif sur tactile
                    cursorShape: Qt.PointingHandCursor
                    onClicked: vehicleMenuPage.StackView.view.pop()
                }
            }

            Text {
                text: "VÉHICULE"
                color: T.Theme.textMain
                font.pixelSize: 22; font.bold: true
                font.letterSpacing: 2
            }
        }

        // --- LISTE DES OPTIONS ---
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: vehicleMenuPage.menuItems
            spacing: 12
            clip: true

            delegate: Rectangle {
                id: menuTile
                width: ListView.view.width
                height: 90
                color: T.Theme.bgDimmed
                radius: 12

                // Illumination de la bordure au toucher
                border.color: tileMouse.pressed || tileMouse.containsMouse ? T.Theme.main : Qt.rgba(1, 1, 1, 0.05)
                border.width: tileMouse.pressed || tileMouse.containsMouse ? 2 : 1

                // Effet tactile d'enfoncement physique
                scale: tileMouse.pressed ? 0.98 : 1.0
                Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }
                Behavior on border.color { ColorAnimation { duration: 150 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 25
                    spacing: 20

                    // Icône (Emoji)
                    Text {
                        text: modelData.icon
                        font.pixelSize: 30
                        Layout.alignment: Qt.AlignVCenter
                    }

                    // Textes
                    Column {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 4
                        Text {
                            text: modelData.label
                            color: T.Theme.textMain
                            font.pixelSize: 20; font.bold: true
                        }
                        Text {
                            text: modelData.desc
                            color: T.Theme.unselected
                            font.pixelSize: 13
                        }
                    }

                    // Flèche de navigation animée
                    Text {
                        text: "〉"
                        color: tileMouse.pressed || tileMouse.containsMouse ? T.Theme.main : T.Theme.unselected
                        font.pixelSize: 20; font.bold: true
                        transform: Translate { x: tileMouse.pressed || tileMouse.containsMouse ? 5 : 0 }
                        Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
                    }
                }

                MouseArea {
                    id: tileMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: vehicleMenuPage.StackView.view.push(Qt.resolvedUrl(modelData.source))
                }
            }
        }
    }
}