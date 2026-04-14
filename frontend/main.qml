import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "views"
import "style"
import "components"

ApplicationWindow {
    id: appWindow
    property string version: bridge.data !== undefined && bridge.data.system_version !== undefined ? bridge.data.system_version : "?.?.?"
    visible: true
    width: 1980
    height: 720
    title: "CliOS v" + version

    visibility: "Maximized"
    flags: Qt.FramelessWindowHint | Qt.Window | Qt.MSWindowsFixedSizeDialogHint

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