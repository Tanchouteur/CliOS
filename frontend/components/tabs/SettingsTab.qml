import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../style" as T // Adapte le chemin si besoin

StackView {
    id: settingsStackView
    anchors.fill: parent

    // 1. LE MODÈLE ENRICHI (Titre + Description)
    readonly property var tiles: [
        { label: "Ambiance", desc: "Éclairage LED, couleurs et thèmes visuels", source: "../pages/AmbiancePage.qml" },
        { label: "Audio",    desc: "Volumes, égaliseur et sources multimédias", source: "../pages/NonBuildPage.qml"    },
        { label: "Véhicule", desc: "Etat vehicule, config et alertes",          source: "../pages/VehiclePage.qml"  },
        { label: "Système",  desc: "Services, ",                                source: "../pages/SystemePage.qml"   }
    ]

    // 2. LA PAGE PRINCIPALE (Grille)
    initialItem: Item {
        id: gridPage

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20

            // --- EN-TÊTE ---
            Text {
                text: "PARAMÈTRES SYSTÈME"
                color: T.Theme.textMain
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
                Layout.alignment: Qt.AlignLeft
            }

            // --- GRILLE DES TUILES ---
            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: 2
                rowSpacing: 16
                columnSpacing: 16

                Repeater {
                    model: settingsStackView.tiles

                    delegate: Rectangle {
                        id: tile
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        // Design de la carte
                        color: T.Theme.bgDimmed
                        radius: 12
                        border.color: tileArea.containsMouse ? T.Theme.main : Qt.rgba(1, 1, 1, 0.05)
                        border.width: tileArea.containsMouse ? 2 : 1

                        // Animation physique au clic (Rétrécissement)
                        scale: tileArea.pressed ? 0.97 : 1.0
                        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                        Behavior on border.color { ColorAnimation { duration: 200 } }

                        // Ligne d'accentuation à gauche
                        Rectangle {
                            width: 4
                            anchors {
                                left: parent.left
                                top: parent.top
                                bottom: parent.bottom
                                margins: 20
                            }
                            radius: 2
                            color: T.Theme.main
                            opacity: tileArea.containsMouse ? 1.0 : 0.5
                            Behavior on opacity { NumberAnimation { duration: 200 } }
                        }

                        // Textes (Titre + Description)
                        Column {
                            anchors {
                                left: parent.left
                                right: chevron.left
                                verticalCenter: parent.verticalCenter
                                leftMargin: 40 // Laisse la place pour la ligne d'accentuation
                                rightMargin: 15
                            }
                            spacing: 6

                            Text {
                                text: modelData.label
                                color: T.Theme.textMain
                                font.pixelSize: 24
                                font.bold: true
                            }
                            Text {
                                text: modelData.desc
                                color: T.Theme.unselected
                                font.pixelSize: 14
                                wrapMode: Text.WordWrap // Coupe le texte s'il est trop long
                                width: parent.width
                            }
                        }

                        // Chevron de navigation à droite
                        Text {
                            id: chevron
                            anchors {
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                rightMargin: 25
                            }
                            text: "〉"
                            color: tileArea.containsMouse ? T.Theme.main : T.Theme.unselected
                            font.pixelSize: 24
                            font.bold: true

                            // Petit effet de glissement au survol
                            transform: Translate { x: tileArea.containsMouse ? 4 : 0 }
                            Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                        }

                        // Zone de clic
                        MouseArea {
                            id: tileArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onClicked: {
                                // On pousse la page dans le StackView
                                settingsStackView.push(Qt.resolvedUrl(modelData.source))
                            }
                        }
                    }
                }
            }
        }
    }
}