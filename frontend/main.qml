import QtQuick
import QtQuick.Controls
import "views"

ApplicationWindow {
    property int version: 1
    visible: true
    width: 1920
    height: 720
    title: "ClioOS v" + version
    color: "#0a0a0c"

    Dash {
        id: dashboardView
        anchors.fill: parent
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