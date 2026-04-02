import QtQuick
import QtQuick.Controls
import "views"

ApplicationWindow {
    visible: true
    width: 1920
    height: 1080
    title: "Clio 3 - OS"
    color: "#0a0a0c"

    BMW_1 {
        id: dashboardView
        anchors.fill: parent
    }


    // --- Indicateur de Pagination ---
    PageIndicator {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter

        // Synchronisation avec le gestionnaire de vues
        currentIndex: viewPager.currentIndex
        count: viewPager.count
    }

    // --- Bannière d'Alerte Télémétrique ---
    Rectangle {
        id: obdAlertBanner
        z: 999 // Maintien au premier plan absolu

        width: 400
        height: 60
        anchors.top: parent.top
        anchors.topMargin: 30
        anchors.horizontalCenter: parent.horizontalCenter

        radius: 10
        color: "#e74c3c"

        // Affichage conditionnel : Uniquement si la rupture de liaison est confirmée par le backend
        visible: bridge.data.connexion_obd_moteur === false

        Text {
            anchors.centerIn: parent
            text: "CONNEXION OBD PERDUE"
            color: "#ffffff"
            font.pixelSize: 22
            font.bold: true
            font.family: "Arial"
        }
    }
}