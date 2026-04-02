import QtQuick
import QtQuick.Controls
import "views"
import "style"

ApplicationWindow {
    id: appWindow
    property int version: 1
    visible: true
    width: 1920
    height: 720
    title: "CliOS v" + version

    // Application de la couleur de fond via le Thème
    color: Theme.bgMain

    Dash {
        id: dashboardView
        anchors.fill: parent
    }

    // --- Bannière d'Alerte Télémétrique ---
    Rectangle {
        id: obdAlertBanner
        z: 999

        width: 400
        height: 60
        anchors.top: parent.top
        anchors.topMargin: 30
        anchors.horizontalCenter: parent.horizontalCenter

        radius: 10
        color: Theme.danger

        visible: bridge.data.connexion_obd_moteur === false

        Text {
            anchors.centerIn: parent
            text: "CONNEXION OBD PERDUE"
            color: Theme.textMain
            font.pixelSize: 22
            font.bold: true
            font.family: "Arial"
        }
    }
}