import QtQuick
import QtQuick.Layouts
import "../style" as T

Item {
    id: root
    anchors.top: parent.top
    anchors.horizontalCenter: parent.horizontalCenter
    width: 660
    height: 90
    z: 9999 // Toujours au premier plan absolu

    property bool isVisible: false
    property string currentLevel: "INFO"
    property string currentTitle: "INFORMATION"
    property string currentMessage: ""
    property color levelColor: T.StyleManager.accent
    property string levelIcon: "◆"
    property int currentDuration: 3500

    // Capsule Flottante de Notification de Prestige
    Rectangle {
        id: capsule
        width: parent.width
        height: 72
        anchors.horizontalCenter: parent.horizontalCenter

        // Animation d'entrée / sortie avec rebond physique
        y: root.isVisible ? 16 : -95
        opacity: root.isVisible ? 1.0 : 0.0
        scale: root.isVisible ? 1.0 : 0.88

        Behavior on y { NumberAnimation { duration: 380; easing.type: Easing.OutBack } }
        Behavior on opacity { NumberAnimation { duration: 260 } }
        Behavior on scale { NumberAnimation { duration: 320; easing.type: Easing.OutBack } }

        radius: 18
        color: "#F0080E18" // Verre fumé profond 94%
        border.width: 1.5
        border.color: root.levelColor

        // Liseré supérieur spéculaire
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            height: 1
            color: Qt.rgba(1, 1, 1, 0.25)
        }

        // Contenu de la notification
        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 14

            // Badge / Gemme de Statut
            Rectangle {
                width: 44
                height: 44
                radius: 22
                color: Qt.rgba(root.levelColor.r, root.levelColor.g, root.levelColor.b, 0.22)
                border.width: 1.5
                border.color: root.levelColor

                Text {
                    anchors.centerIn: parent
                    text: root.levelIcon
                    color: root.levelColor
                    font.pixelSize: 18
                    font.weight: Font.Bold
                }
            }

            // Textes : Tag de niveau & Message
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: root.currentTitle
                    color: root.levelColor
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1.4
                }

                Text {
                    Layout.fillWidth: true
                    text: root.currentMessage
                    color: "#FFFFFF"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
            }

            // Bouton tactile rapide de fermeture
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: Qt.rgba(1, 1, 1, 0.08)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.12)

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: "#BAC8D9"
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.dismiss()
                }
            }
        }

        // Ligne de progression d'auto-destruction (Timer Bar en bas)
        Rectangle {
            id: progressTrack
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottomMargin: 2
            height: 2.5
            radius: 1.25
            color: Qt.rgba(1, 1, 1, 0.08)
            clip: true

            Rectangle {
                id: progressBar
                height: parent.height
                radius: 1.25
                color: root.levelColor
                width: parent.width

                PropertyAnimation {
                    id: progressAnim
                    target: progressBar
                    property: "width"
                    from: progressTrack.width
                    to: 0
                    duration: root.currentDuration > 0 ? root.currentDuration : 1000
                }
            }
        }

        // Clic sur l'ensemble de la capsule pour fermer immédiatement
        MouseArea {
            anchors.fill: parent
            z: -1
            onClicked: root.dismiss()
        }
    }

    function dismiss() {
        root.isVisible = false
        progressAnim.stop()
        autoHideTimer.stop()
    }

    // Minuteur d'auto-fermeture
    Timer {
        id: autoHideTimer
        onTriggered: root.dismiss()
    }

    // Connexion au Signal Python
    Connections {
        target: bridge

        function onNotificationEvent(level, message, duration) {
            const lvl = String(level || "INFO").toUpperCase()
            root.currentMessage = message || ""
            root.currentLevel = lvl
            root.currentDuration = duration > 0 ? duration : 3500

            // Configuration stylistique selon la gravité
            if (lvl === "CRITICAL" || lvl === "ERROR") {
                root.levelColor = T.StyleManager.danger
                root.levelIcon = "▲"
                root.currentTitle = "ALERTE SYSTÈME CRITIQUE"
            } else if (lvl === "WARNING") {
                root.levelColor = T.StyleManager.warning
                root.levelIcon = "!"
                root.currentTitle = "AVERTISSEMENT VÉHICULE"
            } else if (lvl === "OK" || lvl === "SUCCESS") {
                root.levelColor = T.StyleManager.success
                root.levelIcon = "✓"
                root.currentTitle = "CONFIRMATION"
            } else {
                root.levelColor = T.StyleManager.accent
                root.levelIcon = "◆"
                root.currentTitle = "INFORMATION VÉHICULE"
            }

            root.isVisible = true

            // Animation de la barre de progression
            if (root.currentDuration > 0) {
                progressBar.width = progressTrack.width
                progressAnim.duration = root.currentDuration
                progressAnim.restart()

                autoHideTimer.interval = root.currentDuration
                autoHideTimer.restart()
            } else {
                progressBar.width = progressTrack.width
                progressAnim.stop()
                autoHideTimer.stop()
            }
        }
    }
}