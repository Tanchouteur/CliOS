import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../style" as T
import "../state" as S

Item {
    id: root
    anchors.fill: parent
    z: 9998
    visible: opacity > 0.001
    opacity: 0.0

    Behavior on opacity {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }

    property var maintenanceData: ({
        version: S.UiState.systemVersion,
        ip_address: "127.0.0.1",
        wifi_ssid: "",
        overlay_status: "READ_WRITE",
        git_info: "main",
        cpu_temp: ""
    })

    property string confirmAction: ""
    property string confirmTitle: ""
    property string confirmMessage: ""

    function open() {
        refreshStatus()
        confirmAction = ""
        root.opacity = 1.0
    }

    function close() {
        confirmAction = ""
        root.opacity = 0.0
    }

    function toggle() {
        if (root.opacity > 0.5) close()
        else open()
    }

    function refreshStatus() {
        try {
            const raw = bridge.getSystemMaintenanceStatus()
            if (raw) {
                maintenanceData = JSON.parse(raw)
            }
        } catch (e) {
            console.log("Erreur rafraichissement maintenance:", e)
        }
    }

    Timer {
        interval: 3000
        running: root.visible
        repeat: true
        onTriggered: root.refreshStatus()
    }

    // Fond sombre flouté / verre fumé
    Rectangle {
        anchors.fill: parent
        color: "#F2080D14"
        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }
    }

    // Conteneur principal
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 20

        // En-tête avec Titre et Bouton Fermer
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            Rectangle {
                width: 46; height: 46; radius: 12
                color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.18)
                border.width: 1.5; border.color: T.StyleManager.accent
                Text {
                    anchors.centerIn: parent
                    text: "\u2699"
                    font.pixelSize: 22
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "MENU DE MAINTENANCE SYSTÈME"
                    color: "#FFFFFF"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 22
                    font.bold: true
                    font.letterSpacing: 1.2
                }
                Text {
                    text: "Accès direct technicien · CliOS " + S.UiState.systemVersion + " · " + (root.maintenanceData.git_info || "main")
                    color: "#8FA3B8"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 13
                }
            }

            // Bouton Fermer
            Rectangle {
                width: 140; height: 46; radius: 12
                color: "#1E293B"
                border.width: 1.5; border.color: "#334155"

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    Text { text: "\u2715"; color: "#FFFFFF"; font.pixelSize: 16; font.bold: true }
                    Text { text: "FERMER"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.close()
                }
            }
        }

        // Bandeau d état système
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            spacing: 16

            // Carte IP / Réseau Wi-Fi
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                color: "#111827"; border.width: 1; border.color: "#1F2937"
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Text { text: "\uD83C\uDF10"; font.pixelSize: 22 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text {
                            text: root.maintenanceData.wifi_ssid ? "WI-FI · " + root.maintenanceData.wifi_ssid.toUpperCase() : "RÉSEAU IP"
                            color: "#9CA3AF"; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight
                        }
                        Text {
                            text: root.maintenanceData.ip_address || "Hors-ligne"
                            color: root.maintenanceData.ip_address && root.maintenanceData.ip_address !== "Hors-ligne" && root.maintenanceData.ip_address !== "127.0.0.1" ? T.StyleManager.success : "#EF4444"
                            font.pixelSize: 16; font.bold: true; font.family: "Monospace"
                        }
                    }
                }
            }

            // Carte Protection SD
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                color: "#111827"; border.width: 1; border.color: "#1F2937"
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Text { text: root.maintenanceData.overlay_status === "READ_ONLY" ? "\uD83D\uDEE1" : "\u26A0" ; font.pixelSize: 22 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: "PROTECTION CARTE SD"; color: "#9CA3AF"; font.pixelSize: 11; font.bold: true }
                        Text {
                            text: root.maintenanceData.overlay_status === "READ_ONLY" ? "LECTURE SEULE (PROTÉGÉE)" : "ÉCRITURE (STANDARD)"
                            color: root.maintenanceData.overlay_status === "READ_ONLY" ? T.StyleManager.success : T.StyleManager.warning
                            font.pixelSize: 14; font.bold: true
                        }
                    }
                }
            }

            // Carte CPU / RAM
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                color: "#111827"; border.width: 1; border.color: "#1F2937"
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Text { text: "\u26A1"; font.pixelSize: 22 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: "CHARGE SYSTÈME"; color: "#9CA3AF"; font.pixelSize: 11; font.bold: true }
                        Text {
                            text: S.UiState.fixed(S.UiState.appCpuTotalPct, 0, "0") + "% CPU · " + S.UiState.fixed(S.UiState.appRamMb, 0, "0") + " MB" + (root.maintenanceData.cpu_temp ? " · " + root.maintenanceData.cpu_temp : "")
                            color: "#E5E7EB"; font.pixelSize: 14; font.bold: true; font.family: "Monospace"
                        }
                    }
                }
            }
        }

        // Grille des 6 Boutons d Action Tactile
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 16
            rowSpacing: 16

            // 1. Mettre à jour (Git Pull)
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#131C2E"; border.width: 1.5; border.color: T.StyleManager.accent
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\u2B07"; font.pixelSize: 28 }
                        Text { text: "METTRE À JOUR"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Exécute git pull pour télécharger les dernières fonctionnalités."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        bridge.triggerGitUpdate()
                    }
                }
            }

            // 2. Basculer SD Read-Only
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#161E2E"; border.width: 1.5; border.color: "#3B82F6"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\uD83D\uDEE1"; font.pixelSize: 28 }
                        Text { text: "BASCULE MODE SD"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Active ou désactive la protection en écriture OverlayFS de la carte SD."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.confirmAction = "toggle_sd"
                        root.confirmTitle = "Bascule protection SD ?"
                        root.confirmMessage = "L état de protection en lecture seule de la carte SD va être modifié. Un redémarrage sera requis."
                    }
                }
            }

            // 3. Relancer CliOS
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#16222F"; border.width: 1.5; border.color: "#0EA5E9"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\uD83D\uDD04"; font.pixelSize: 28 }
                        Text { text: "RELANCER CLIOS"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Redémarre l application sans redémarrer le système d exploitation."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        bridge.restartApplication()
                    }
                }
            }

            // 4. Quitter vers Bureau
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#241A1A"; border.width: 1.5; border.color: "#78350F"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\uD83D\uDDA5"; font.pixelSize: 28 }
                        Text { text: "QUITTER CLIOS"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Ferme proprement les services et retourne au bureau ou au shell."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.confirmAction = "quit"
                        root.confirmTitle = "Quitter CliOS ?"
                        root.confirmMessage = "L interface va se fermer et les services de communication CAN seront arrêtés."
                    }
                }
            }

            // 5. Redémarrer le Raspberry Pi
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#2D1D13"; border.width: 1.5; border.color: "#F97316"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\uD83D\uDD01"; font.pixelSize: 28 }
                        Text { text: "REBOOT RASPBERRY"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Arrête les services et redémarre complètement le Raspberry Pi."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.confirmAction = "reboot"
                        root.confirmTitle = "Redémarrer le Raspberry Pi ?"
                        root.confirmMessage = "L ordinateur de bord va s éteindre puis redémarrer complètement."
                    }
                }
            }

            // 6. Éteindre le Véhicule
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 16
                color: "#2C1214"; border.width: 1.5; border.color: "#EF4444"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                    RowLayout {
                        spacing: 12
                        Text { text: "\u23FB"; font.pixelSize: 28 }
                        Text { text: "ÉTEINDRE SYSTÈME"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Sauvegarde les données de trajet et coupe l alimentation en sécurité."
                        color: "#94A3B8"; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.confirmAction = "shutdown"
                        root.confirmTitle = "Éteindre le système ?"
                        root.confirmMessage = "Le Raspberry Pi et tous les services vont s arrêter en toute sécurité."
                    }
                }
            }
        }
    }

    // Boîte de dialogue de confirmation tactile
    Rectangle {
        id: confirmDialogBox
        anchors.fill: parent
        color: "#E0000000"
        visible: root.confirmAction !== ""
        z: 9999

        Rectangle {
            anchors.centerIn: parent
            width: 580; height: 280
            radius: 20
            color: "#182232"
            border.width: 2
            border.color: T.StyleManager.accent

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 16

                Text {
                    text: root.confirmTitle
                    color: "#FFFFFF"
                    font.pixelSize: 22
                    font.bold: true
                }

                Text {
                    Layout.fillWidth: true
                    text: root.confirmMessage
                    color: "#CBD5E1"
                    font.pixelSize: 15
                    wrapMode: Text.WordWrap
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    Rectangle {
                        Layout.fillWidth: true; height: 50; radius: 12
                        color: "#334155"
                        Text { anchors.centerIn: parent; text: "ANNULER"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 15 }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.confirmAction = ""
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true; height: 50; radius: 12
                        color: root.confirmAction === "shutdown" || root.confirmAction === "reboot" ? "#EF4444" : T.StyleManager.accent
                        Text { anchors.centerIn: parent; text: "CONFIRMER"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 15 }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                const act = root.confirmAction
                                root.confirmAction = ""
                                if (act === "toggle_sd") bridge.toggleOverlayFs()
                                else if (act === "quit") bridge.quitApplication()
                                else if (act === "reboot") bridge.rebootSystem()
                                else if (act === "shutdown") bridge.shutdownSystem()
                            }
                        }
                    }
                }
            }
        }
    }
}
