import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Item {
    id: statsPage

    // --- VARIABLES DE PRIX ---
    property real fuelPrice: 1.85

    // Récupération de la valeur du backend au chargement de la page
    Component.onCompleted: {
        if (bridge.stats && bridge.stats.fuel_price !== undefined) {
            statsPage.fuelPrice = bridge.stats.fuel_price
        }
    }

    // ----------------------------------------------------
    // 1. HEADER STRICTEMENT ANCRÉ EN HAUT
    // ----------------------------------------------------
    Item {
        id: header
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            topMargin: 20
            leftMargin: 30
            rightMargin: 30
        }
        height: 50

        // Bouton Retour (Gauche)
        MouseArea {
            id: backBtn
            width: 150
            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
            }
            cursorShape: Qt.PointingHandCursor
            onClicked: statsPage.StackView.view.pop()

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Text {
                    text: "〈 "
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 26
                    font.bold: true
                    transform: Translate { x: backBtn.containsMouse ? -4 : 0 }
                    Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                }
                Text {
                    text: "Retour"
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 20
                    font.bold: true
                }
            }
        }

        // Titre (Centre)
        Text {
            anchors.centerIn: parent
            text: "COÛTS & STATISTIQUES"
            color: T.Theme.textMain
            font.pixelSize: 22
            font.bold: true
            font.letterSpacing: 2
        }
    }

    // ----------------------------------------------------
    // 2. ZONE DES CARTES
    // ----------------------------------------------------
    Row {
        id: cardContainer
        anchors {
            top: header.bottom
            bottom: parent.bottom
            left: parent.left
            right: parent.right
            margins: 30
            topMargin: 20
        }
        spacing: 30

        // --- CARTE GAUCHE : CARBURANT ---
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)

            Column {
                anchors.centerIn: parent
                spacing: 40

                Column {
                    spacing: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                    Text {
                        text: "COÛT DU CARBURANT"
                        color: T.Theme.textMain
                        font.pixelSize: 16
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: "Utilisé pour les statistiques de trajet"
                        color: T.Theme.unselected
                        font.pixelSize: 13
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }

                // --- SÉLECTEUR TACTILE (+ / -) ---
                Row {
                    spacing: 15
                    anchors.horizontalCenter: parent.horizontalCenter

                    // Bouton Moins
                    Rectangle {
                        width: 65; height: 65; radius: 12
                        color: minusArea.pressed ? T.Theme.main : T.Theme.bgMain
                        border.color: Qt.rgba(1, 1, 1, 0.1)

                        Text {
                            anchors.centerIn: parent; text: "−"
                            color: minusArea.pressed ? T.Theme.bgMain : T.Theme.textMain
                            font.pixelSize: 32; font.bold: true
                        }

                        MouseArea {
                            id: minusArea
                            anchors.fill: parent
                            onClicked: {
                                // Arrondi mathématique pour éviter les bugs de flottants en JS
                                statsPage.fuelPrice = Math.max(0.0, Math.round((statsPage.fuelPrice - 0.01) * 100) / 100)
                                bridge.updateFuelPrice(statsPage.fuelPrice)
                            }

                            Timer {
                                interval: 100; running: minusArea.pressed; repeat: true
                                onTriggered: {
                                    statsPage.fuelPrice = Math.max(0.0, Math.round((statsPage.fuelPrice - 0.01) * 100) / 100)
                                    bridge.updateFuelPrice(statsPage.fuelPrice)
                                }
                            }
                        }
                    }

                    // Afficheur
                    Rectangle {
                        width: 140; height: 65; radius: 12
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: statsPage.fuelPrice.toFixed(2) + " €/L"
                            color: T.Theme.main
                            font.pixelSize: 30
                            font.bold: true
                        }
                    }

                    // Bouton Plus
                    Rectangle {
                        width: 65; height: 65; radius: 12
                        color: plusArea.pressed ? T.Theme.main : T.Theme.bgMain
                        border.color: Qt.rgba(1, 1, 1, 0.1)

                        Text {
                            anchors.centerIn: parent; text: "+"
                            color: plusArea.pressed ? T.Theme.bgMain : T.Theme.textMain
                            font.pixelSize: 32; font.bold: true
                        }

                        MouseArea {
                            id: plusArea
                            anchors.fill: parent
                            onClicked: {
                                statsPage.fuelPrice = Math.round((statsPage.fuelPrice + 0.01) * 100) / 100
                                bridge.updateFuelPrice(statsPage.fuelPrice)
                            }

                            Timer {
                                interval: 100; running: plusArea.pressed; repeat: true
                                onTriggered: {
                                    statsPage.fuelPrice = Math.round((statsPage.fuelPrice + 0.01) * 100) / 100
                                    bridge.updateFuelPrice(statsPage.fuelPrice)
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- CARTE DROITE : DIAGNOSTIC / MAINTENANCE ---
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)
            opacity: 0.4

            Column {
                anchors.centerIn: parent
                spacing: 20

                Text {
                    text: "MAINTENANCE"
                    color: T.Theme.textMain
                    font.pixelSize: 16
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: "Remise à zéro des compteurs\n(Disponible prochainement)"
                    color: T.Theme.unselected
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
}