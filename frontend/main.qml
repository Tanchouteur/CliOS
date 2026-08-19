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

    // Réception des événements de maintien 4 doigts depuis le filtre C++/Python (aucun blocage tactile QML)
    Connections {
        target: bridge
        ignoreUnknownSignals: true
        function onOpenMaintenanceRequested() {
            holdAnim.stop()
            holdProgressBar.width = 0
            holdIndicator.visible = false
            maintenanceOverlay.open()
        }
        function onMaintenanceHoldProgressChanged(active) {
            if (active && !maintenanceOverlay.visible) {
                holdIndicator.visible = true
                holdAnim.restart()
            } else {
                holdAnim.stop()
                holdProgressBar.width = 0
                holdIndicator.visible = false
            }
        }
    }

    // Indicateur visuel discret lors du maintien à 4 doigts
    Rectangle {
        id: holdIndicator
        anchors.centerIn: parent
        width: 320
        height: 64
        radius: 32
        color: "#F00F172A"
        border.width: 2
        border.color: StyleManager.accent
        z: 9997
        visible: false
        clip: true

        RowLayout {
            anchors.centerIn: parent
            spacing: 12
            Text {
                text: "🛠️"
                font.pixelSize: 22
            }
            ColumnLayout {
                spacing: 2
                Text {
                    text: "Accès Maintenance..."
                    color: "#FFFFFF"
                    font.family: StyleManager.fontFamily
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    text: "Maintenez 4 doigts appuyés"
                    color: "#94A3B8"
                    font.family: StyleManager.fontFamily
                    font.pixelSize: 11
                }
            }
        }

        // Barre de progression en bas de la capsule
        Rectangle {
            id: holdProgressBar
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            height: 4
            radius: 2
            color: StyleManager.accent
            width: 0

            NumberAnimation {
                id: holdAnim
                target: holdProgressBar
                property: "width"
                from: 0
                to: holdIndicator.width
                duration: 4000
            }
        }
    }

    // Raccourci secret tactile 1 doigt dans le coin supérieur droit (5 clics rapides ou appui long 3s)
    Item {
        anchors.top: parent.top
        anchors.right: parent.right
        width: 70
        height: 70
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
