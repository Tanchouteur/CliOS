import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Item {
    id: statsPage

    property real fuelPrice: 1.85
    property real fuelUsedB: 0.0
    property real distanceB: 0.0

    Component.onCompleted: {
        if (bridge.stats) {
            if (bridge.stats.fuel_price !== undefined) statsPage.fuelPrice = bridge.stats.fuel_price
            if (bridge.stats.trip_b_fuel !== undefined) statsPage.fuelUsedB = bridge.stats.trip_b_fuel
            if (bridge.stats.trip_b !== undefined) statsPage.distanceB = bridge.stats.trip_b
        }
    }

    Item {
        id: header
        anchors {
            top: parent.top; left: parent.left; right: parent.right
            topMargin: 20; leftMargin: 30; rightMargin: 30
        }
        height: 50

        MouseArea {
            id: backBtn
            width: 150
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            cursorShape: Qt.PointingHandCursor
            onClicked: statsPage.StackView.view.pop()

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Text {
                    text: "〈 "
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 26; font.bold: true
                    transform: Translate { x: backBtn.containsMouse ? -4 : 0 }
                    Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                }
                Text {
                    text: "Retour"
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 20; font.bold: true
                }
            }
        }

        Text {
            anchors.centerIn: parent
            text: "COÛTS & STATISTIQUES"
            color: T.Theme.textMain
            font.pixelSize: 22; font.bold: true; font.letterSpacing: 2
        }
    }

    Row {
        id: cardContainer
        anchors {
            top: header.bottom; bottom: parent.bottom
            left: parent.left; right: parent.right
            margins: 30; topMargin: 20
        }
        spacing: 30

        /* CARTE GAUCHE : CARBURANT */
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)

            Column {
                anchors.centerIn: parent
                spacing: 35

                Column {
                    spacing: 20
                    anchors.horizontalCenter: parent.horizontalCenter

                    Column {
                        spacing: 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text { text: "COÛT DU CARBURANT"; color: T.Theme.textMain; font.pixelSize: 16; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: "Utilisé pour les statistiques de trajet"; color: T.Theme.unselected; font.pixelSize: 13; anchors.horizontalCenter: parent.horizontalCenter }
                    }

                    Row {
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: minusArea.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "−"; color: minusArea.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

                            MouseArea {
                                id: minusArea
                                anchors.fill: parent
                                onClicked: {
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

                        Rectangle {
                            width: 140; height: 65; radius: 12
                            color: "transparent"
                            Text { anchors.centerIn: parent; text: statsPage.fuelPrice.toFixed(2) + " €/L"; color: T.Theme.main; font.pixelSize: 30; font.bold: true }
                        }

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: plusArea.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "+"; color: plusArea.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

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

                Rectangle {
                    width: parent.width * 0.7; height: 1
                    color: Qt.rgba(1, 1, 1, 0.1)
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Column {
                    spacing: 20
                    anchors.horizontalCenter: parent.horizontalCenter

                    Column {
                        spacing: 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text { text: "CARBURANT CONSOMMÉ (TRIP B)"; color: T.Theme.textMain; font.pixelSize: 16; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: "Ajustement manuel (Litres)"; color: T.Theme.unselected; font.pixelSize: 13; anchors.horizontalCenter: parent.horizontalCenter }
                    }

                    Row {
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: minusAreaFuel.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "−"; color: minusAreaFuel.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

                            MouseArea {
                                id: minusAreaFuel
                                anchors.fill: parent
                                onClicked: {
                                    statsPage.fuelUsedB = Math.max(0.0, Math.round((statsPage.fuelUsedB - 0.1) * 10) / 10)
                                    bridge.updateTripBFuel(statsPage.fuelUsedB)
                                }
                                Timer {
                                    interval: 100; running: minusAreaFuel.pressed; repeat: true
                                    onTriggered: {
                                        statsPage.fuelUsedB = Math.max(0.0, Math.round((statsPage.fuelUsedB - 0.1) * 10) / 10)
                                        bridge.updateTripBFuel(statsPage.fuelUsedB)
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: 140; height: 65; radius: 12
                            color: "transparent"
                            Text { anchors.centerIn: parent; text: statsPage.fuelUsedB.toFixed(1) + " L"; color: T.Theme.main; font.pixelSize: 30; font.bold: true }
                        }

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: plusAreaFuel.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "+"; color: plusAreaFuel.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

                            MouseArea {
                                id: plusAreaFuel
                                anchors.fill: parent
                                onClicked: {
                                    statsPage.fuelUsedB = Math.round((statsPage.fuelUsedB + 0.1) * 10) / 10
                                    bridge.updateTripBFuel(statsPage.fuelUsedB)
                                }
                                Timer {
                                    interval: 100; running: plusAreaFuel.pressed; repeat: true
                                    onTriggered: {
                                        statsPage.fuelUsedB = Math.round((statsPage.fuelUsedB + 0.1) * 10) / 10
                                        bridge.updateTripBFuel(statsPage.fuelUsedB)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        /* CARTE DROITE : DISTANCE ET MAINTENANCE */
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)

            Column {
                anchors.centerIn: parent
                spacing: 35

                Column {
                    spacing: 20
                    anchors.horizontalCenter: parent.horizontalCenter

                    Column {
                        spacing: 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text { text: "DISTANCE PARCOURUE (TRIP B)"; color: T.Theme.textMain; font.pixelSize: 16; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: "Ajustement manuel (km)"; color: T.Theme.unselected; font.pixelSize: 13; anchors.horizontalCenter: parent.horizontalCenter }
                    }

                    Row {
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: minusAreaDist.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "−"; color: minusAreaDist.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

                            MouseArea {
                                id: minusAreaDist
                                anchors.fill: parent
                                onClicked: {
                                    statsPage.distanceB = Math.max(0.0, Math.round((statsPage.distanceB - 1.0) * 10) / 10)
                                    bridge.updateTripBDistance(statsPage.distanceB)
                                }
                                Timer {
                                    interval: 100; running: minusAreaDist.pressed; repeat: true
                                    onTriggered: {
                                        statsPage.distanceB = Math.max(0.0, Math.round((statsPage.distanceB - 1.0) * 10) / 10)
                                        bridge.updateTripBDistance(statsPage.distanceB)
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: 140; height: 65; radius: 12
                            color: "transparent"
                            Text { anchors.centerIn: parent; text: statsPage.distanceB.toFixed(1) + " km"; color: T.Theme.main; font.pixelSize: 30; font.bold: true }
                        }

                        Rectangle {
                            width: 65; height: 65; radius: 12
                            color: plusAreaDist.pressed ? T.Theme.main : T.Theme.bgMain
                            border.color: Qt.rgba(1, 1, 1, 0.1)

                            Text { anchors.centerIn: parent; text: "+"; color: plusAreaDist.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 32; font.bold: true }

                            MouseArea {
                                id: plusAreaDist
                                anchors.fill: parent
                                onClicked: {
                                    statsPage.distanceB = Math.round((statsPage.distanceB + 1.0) * 10) / 10
                                    bridge.updateTripBDistance(statsPage.distanceB)
                                }
                                Timer {
                                    interval: 100; running: plusAreaDist.pressed; repeat: true
                                    onTriggered: {
                                        statsPage.distanceB = Math.round((statsPage.distanceB + 1.0) * 10) / 10
                                        bridge.updateTripBDistance(statsPage.distanceB)
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width * 0.7; height: 1
                    color: Qt.rgba(1, 1, 1, 0.1)
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Column {
                    spacing: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                    opacity: 0.4
                    Text { text: "MAINTENANCE"; color: T.Theme.textMain; font.pixelSize: 16; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: "Remise à zéro des compteurs\n(Disponible prochainement)"; color: T.Theme.unselected; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; anchors.horizontalCenter: parent.horizontalCenter }
                }
            }
        }
    }
}