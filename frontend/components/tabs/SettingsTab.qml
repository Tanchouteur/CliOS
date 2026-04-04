import QtQuick 2.15
import QtQuick.Controls 2.15 // NOUVEAU : Indispensable pour avoir accès à StackView
import QtQuick.Layouts 1.15
import "../../style" as T

// 1. La racine devient un StackView avec un ID précis
StackView {
    id: settingsStackView

    // Propriété déplacée ici pour être accessible par le composant enfant
    readonly property var tiles: [
        // Attention au chemin : si AmbiancePage.qml est dans le même dossier
        // que SettingsTab.qml, on met juste le nom du fichier !
        { label: "Ambiant", source: "AmbiancePage.qml" },
        { label: "Audio",   source: "AudioPage.qml"    },
        { label: "Vehicle", source: "VehiclePage.qml"  },
        { label: "System",  source: "SystemPage.qml"   }
    ]

    // 2. La page de base (ta grille) est définie comme "initialItem"
    initialItem: Item {
        id: gridPage

        GridLayout {
            anchors.fill: parent
            anchors.margins: 16
            columns: 2
            rowSpacing: 14
            columnSpacing: 14

            Repeater {
                // On va chercher la variable "tiles" sur le parent (le StackView)
                model: settingsStackView.tiles

                delegate: Rectangle {
                    id: tile
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "transparent"
                    radius: 12
                    border.color: T.Theme.mainLight
                    border.width: 1.5

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: tileArea.pressed ? Qt.rgba(1, 1, 1, 0.08) : tileArea.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent"
                        Behavior on color { ColorAnimation { duration: 100 } }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: T.Theme.textMain
                        font.pixelSize: 26
                        font.weight: Font.Light
                    }

                    MouseArea {
                        id: tileArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: {
                            console.log("Settings →", modelData.label)
                            // 3. CA MARCHE : On appelle l'ID de notre StackView !
                            settingsStackView.push(Qt.resolvedUrl(modelData.source))
                        }
                    }
                }
            }
        }
    }
}