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

    // Raccourci secret tactile dans le coin supérieur droit (5 clics rapides ou appui long 3s)
    // Ne bloque aucun toucher sur le reste de l'écran
    Item {
        anchors.top: parent.top
        anchors.right: parent.right
        width: 80
        height: 80
        z: 9996

        property int tapCount: 0
        Timer {
            id: secretTapReset
            interval: 1200
            onTriggered: parent.tapCount = 0
        }

        MouseArea {
            anchors.fill: parent
            pressAndHoldInterval: 3000
            onClicked: {
                parent.tapCount += 1
                secretTapReset.restart()
                if (parent.tapCount >= 5) {
                    parent.tapCount = 0
                    maintenanceOverlay.toggle()
                }
            }
            onPressAndHold: {
                parent.tapCount = 0
                maintenanceOverlay.open()
            }
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
