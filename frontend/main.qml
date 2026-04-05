import QtQuick
import QtQuick.Controls
import "views"
import "style"
import "components"

ApplicationWindow {
    id: appWindow
    property string version: "1.1.2"
    visible: true
    width: 1920
    height: 700
    title: "CliOS v" + version

    // Application de la couleur de fond via le Thème
    color: Theme.bgMain

    Dash {
        id: dashboardView
        anchors.fill: parent
    }

    // --- Bannière d'Alerte Télémétrique ---
    NotificationCenter {
        id: notifCenter
        z: 9999 // Toujours au premier plan
    }
}