import QtQuick
import QtQuick.Controls
import "../style" as T

Item {
    id: root

    // Ancrage au centre-haut de l'écran
    anchors.top: parent.top
    anchors.horizontalCenter: parent.horizontalCenter
    width: 450
    height: 100
    z: 9999 // Toujours au premier plan

    // État local d'affichage
    property bool isVisible: false

    // Le visuel de la notification (Toast)
    Rectangle {
        id: toastRect
        width: parent.width
        height: 60
        anchors.horizontalCenter: parent.horizontalCenter

        // Moteur d'animation (glissement Y + opacité)
        y: root.isVisible ? 20 : -80
        opacity: root.isVisible ? 1.0 : 0.0

        radius: 12
        color: T.Theme.bgDimmed
        border.width: 2

        Behavior on y { NumberAnimation { duration: 400; easing.type: Easing.OutBack } }
        Behavior on opacity { NumberAnimation { duration: 300 } }

        Text {
            id: toastMsg
            anchors.centerIn: parent
            color: T.Theme.textMain
            font.pixelSize: 20
            font.bold: true
            font.letterSpacing: 1
        }
    }

    // Minuteur d'auto-destruction
    Timer {
        id: autoHideTimer
        onTriggered: root.isVisible = false
    }

    // Connexion au Signal Python
    Connections {
        target: bridge

        function onNotificationEvent(level, message, duration) {
            console.log("[DEBUG QML] Notification reçue : " + level + " | " + message)
            toastMsg.text = message

            // Stylisation dynamique selon la gravité
            if (level === "CRITICAL") {
                toastRect.border.color = T.Theme.danger
                toastRect.color = Qt.rgba(231/255, 76/255, 60/255, 0.2) // Fond rouge translucide
            }
            else if (level === "WARNING") {
                toastRect.border.color = T.Theme.warning
                toastRect.color = Qt.rgba(230/255, 126/255, 34/255, 0.2) // Fond orange translucide
            }
            else { // INFO ou autre
                toastRect.border.color = T.Theme.info
                toastRect.color = Qt.rgba(52/255, 152/255, 219/255, 0.2) // Fond bleu translucide
            }

            // Déclenche l'animation d'apparition
            root.isVisible = true

            // Gestion de la durée (0 = persistant)
            if (duration > 0) {
                autoHideTimer.interval = duration
                autoHideTimer.restart()
            } else {
                autoHideTimer.stop()
            }
        }
    }
}