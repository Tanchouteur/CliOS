import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../style" as T

Item {
    id: statsPage
    property real fuelPrice: bridge.stats.fuel_price || 1.85

    // Header avec bouton retour
    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 20; leftMargin: 30 }
        height: 50

        Text {
            text: "〈  COÛTS & STATS"
            color: T.Theme.textMain
            font.pixelSize: 20; font.bold: true
            MouseArea { anchors.fill: parent; onClicked: statsPage.StackView.view.pop() }
        }
    }

    // Ton bloc de réglage de carburant (réutilisé de ton code)
    Rectangle {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; margins: 30 }
        color: T.Theme.bgDimmed; radius: 16

        Column {
            anchors.centerIn: parent; spacing: 40
            Text { text: "RÉGLAGE PRIX CARBURANT"; color: T.Theme.textMain; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }

            Row {
                spacing: 20; anchors.horizontalCenter: parent.horizontalCenter
                // ... (Ici tu remets tes boutons +/- et l'afficheur de ton code original)
                // Appeler bridge.updateFuelPrice(statsPage.fuelPrice)
            }
        }
    }
}