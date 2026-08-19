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

    // Détecteur tactile multi-points : 4 doigts maintenus 4 secondes
    MultiPointTouchArea {
        id: touchSensor
        anchors.fill: parent
        mouseEnabled: false
        touchPoints: [
            TouchPoint { id: tp1 },
            TouchPoint { id: tp2 },
            TouchPoint { id: tp3 },
            TouchPoint { id: tp4 }
        ]

        readonly property int touchCount: (tp1.pressed ? 1 : 0) + (tp2.pressed ? 1 : 0) + (tp3.pressed ? 1 : 0) + (tp4.pressed ? 1 : 0)
        readonly property bool fourFingersActive: touchCount >= 4

        onFourFingersActiveChanged: {
            if (fourFingersActive && !maintenanceOverlay.visible) {
                holdTimer.start()
                holdAnim.restart()
            } else {
                holdTimer.stop()
                holdAnim.stop()
                holdProgressBar.width = 0
            }
        }
    }

    Timer {
        id: holdTimer
        interval: 4000
        repeat: false
        onTriggered: {
            holdAnim.stop()
            holdProgressBar.width = 0
            maintenanceOverlay.open()
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
        visible: touchSensor.fourFingersActive && !maintenanceOverlay.visible
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
