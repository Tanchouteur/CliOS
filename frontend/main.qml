import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "style"
import "components"
import "state" as S

ApplicationWindow {
    id: appWindow
    property string version: S.UiState.systemVersion
    visible: true
    width: 1920
    height: 720
    title: "CliOS v" + version

    visibility: Window.FullScreen
    flags: Qt.FramelessWindowHint | Qt.Window | Qt.MSWindowsFixedSizeDialogHint

    color: Theme.bgMain

    Loader {
        id: dashboardLoader
        anchors.fill: parent
        source: Qt.resolvedUrl(StyleManager.dashboardSource)
    }



    // Écoute des demandes d'ouverture de maintenance depuis les pages de réglages
    Connections {
        target: bridge
        ignoreUnknownSignals: true
        function onOpenMaintenanceRequested() {
            maintenanceOverlay.open()
        }
    }

    // Menu de maintenance (tactile et plein écran)
    MaintenanceOverlay {
        id: maintenanceOverlay
        z: 9998
    }

    // Raccourci clavier de secours pour le dev / test (F12 ou Ctrl+M)
    Item {
        focus: true
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_F12 || (event.key === Qt.Key_M && (event.modifiers & Qt.ControlModifier))) {
                maintenanceOverlay.toggle()
                event.accepted = true
            }
        }
    }

    NotificationCenter {
        id: notifCenter
        z: 9999 // Toujours au premier plan
    }
}
