import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 1920
    height: 720
    anchors.fill: parent
    visible: opacity > 0.01
    opacity: 0.0
    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    signal closeRequested()
    signal navigateRequested(string target)
    signal actionRequested(string action)

    property int activeTab: 0 // 0: Pages & Réglages, 1: Données Trajet, 2: Actions & Alimentation

    function open() {
        opacity = 1.0
    }

    function close() {
        opacity = 0.0
        root.closeRequested()
    }

    // Fond sombre semi-transparent
    Rectangle {
        anchors.fill: parent
        color: "#F205080C"
        MouseArea { anchors.fill: parent; onClicked: root.close() }
    }

    // Panneau de contrôle central Mugen Sport
    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: 1440
        height: 630
        radius: 18
        color: "#0D121A"
        border.width: 1.8
        border.color: "#222D3E"

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // =================================================================
            // 1. EN-TÊTE DU MENU & SÉLECTEUR D'ONGLETS
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Row {
                    spacing: 12
                    Rectangle {
                        width: 36; height: 36; radius: 18
                        color: "#FF2B1C"
                        Text { anchors.centerIn: parent; text: "無限"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
                    }
                    Column {
                        Text {
                            text: "MENU PRINCIPAL CliOS · MUGEN POWER"
                            color: "#FFFFFF"
                            font.family: "Arial, sans-serif"
                            font.pixelSize: 18
                            font.weight: Font.Bold
                            font.letterSpacing: 1.2
                        }
                        Text {
                            text: "Accès centralisé à l'ensemble des modules, réglages et diagnostics du véhicule"
                            color: "#8FA3B8"
                            font.pixelSize: 12
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Onglets de navigation interne au menu
                RowLayout {
                    spacing: 8

                    Repeater {
                        model: [
                            { id: 0, title: "PAGES & CONFIGURATION" },
                            { id: 1, title: "TRAJET & MÉTROLOGIE" },
                            { id: 2, title: "ACTIONS RAPIDES & SYSTÈME" }
                        ]

                        Rectangle {
                            width: 190
                            height: 38
                            radius: 19
                            property bool isSelected: root.activeTab === modelData.id
                            color: isSelected ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.22) : "#141C28"
                            border.width: 1.2
                            border.color: isSelected ? T.StyleManager.accent : "#243346"

                            Text {
                                anchors.centerIn: parent
                                text: modelData.title
                                color: isSelected ? "#FFFFFF" : "#8FA3B8"
                                font.family: "Arial, sans-serif"
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                font.letterSpacing: 0.8
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = modelData.id
                            }
                        }
                    }
                }

                // Bouton Fermer (X)
                Rectangle {
                    width: 38
                    height: 38
                    radius: 19
                    color: "#182230"
                    border.width: 1
                    border.color: "#2C3F58"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "#FFFFFF"
                        font.pixelSize: 16
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: "#1E2A3A" }

            // =================================================================
            // 2. CONTENU DES ONGLETS
            // =================================================================
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // -------------------------------------------------------------
                // ONGLET 0 : PAGES & CONFIGURATION DU VÉHICULE
                // -------------------------------------------------------------
                GridLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 0
                    columns: 3
                    columnSpacing: 16
                    rowSpacing: 16

                    // Modèle des pages disponibles
                    Repeater {
                        model: [
                            { id: "vehicle", icon: "🚗", title: "Véhicule & Profils", desc: "Gestion des profils de voiture (Clio 3 RS, Diesel), étalonnage des rapports de boîte et suivi révision." },
                            { id: "appearance", icon: "🎨", title: "Apparence & Thèmes", desc: "Sélecteur de style graphique, roue chromatique HSV et personnalisation de l'ambiance LED." },
                            { id: "services", icon: "⚙️", title: "Services & Carburant", desc: "Supervision des services en temps réel, réglage du prix du litre d'essence et diagnostics." },
                            { id: "system", icon: "💻", title: "Santé Système & SD", desc: "Surveillance CPU/RAM, stockage USB, mode SD OverlayFS, diagnostic et maintenance." },
                            { id: "diagnostic", icon: "🔍", title: "Diagnostic Moteur OBD2", desc: "Scan complet du calculateur d'injection ISO-TP et consultation des codes défauts DTC." },
                            { id: "developer", icon: "⚡", title: "Trames CAN Développeur", desc: "Moniteur des signaux CAN bruts normalisés en temps réel et qualité de réception." }
                        ]

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: "#121924"
                            border.width: 1.2
                            border.color: "#1F2B3C"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Text { text: modelData.icon; font.pixelSize: 24 }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.title
                                        color: "#FFFFFF"
                                        font.family: "Arial, sans-serif"
                                        font.pixelSize: 16
                                        font.weight: Font.Bold
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: modelData.desc
                                    color: "#8FA3B8"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 38
                                    radius: 8
                                    color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.18)
                                    border.width: 1
                                    border.color: T.StyleManager.accent

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 6
                                        Text { text: "OUVRIR LA PAGE"; color: "#FFFFFF"; font.pixelSize: 12; font.bold: true; font.letterSpacing: 0.8 }
                                        Text { text: "→"; color: T.StyleManager.accent; font.pixelSize: 14; font.bold: true }
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.close()
                                    root.navigateRequested(modelData.id)
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // ONGLET 1 : STATISTIQUES DU TRAJET & MÉTROLOGIE
                // -------------------------------------------------------------
                RowLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 1
                    spacing: 16

                    // Synthèse session en cours
                    Rectangle {
                        Layout.preferredWidth: 680
                        Layout.fillHeight: true
                        radius: 12
                        color: "#121924"
                        border.width: 1.2
                        border.color: "#1F2B3C"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "SESSION ACTIVE"
                                color: T.StyleManager.accent
                                font.family: "Arial, sans-serif"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 14
                                rowSpacing: 14

                                Rectangle {
                                    Layout.fillWidth: true; height: 80; radius: 8; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                    Column {
                                        anchors.centerIn: parent; spacing: 2
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "DISTANCE TRAJET"; color: "#8FA3B8"; font.pixelSize: 11; font.bold: true }
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripDistance, 1, "0.0") + " km"; color: "#FFFFFF"; font.pixelSize: 22; font.bold: true }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; height: 80; radius: 8; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                    Column {
                                        anchors.centerIn: parent; spacing: 2
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "CARBURANT BRÛLÉ"; color: "#8FA3B8"; font.pixelSize: 11; font.bold: true }
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripFuelLiters, 2, "0.00") + " L"; color: "#FFFFFF"; font.pixelSize: 22; font.bold: true }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; height: 80; radius: 8; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                    Column {
                                        anchors.centerIn: parent; spacing: 2
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "COÛT FINANCIER"; color: "#8FA3B8"; font.pixelSize: 11; font.bold: true }
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripCost, 2, "0.00") + " €"; color: T.StyleManager.accent; font.pixelSize: 22; font.bold: true }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; height: 80; radius: 8; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                    Column {
                                        anchors.centerIn: parent; spacing: 2
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "AUTONOMIE ESTIMÉE"; color: "#8FA3B8"; font.pixelSize: 11; font.bold: true }
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.autonomy, 0, "0") + " km"; color: "#FFFFFF"; font.pixelSize: 22; font.bold: true }
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Rectangle {
                                    Layout.fillWidth: true; height: 46; radius: 8
                                    color: S.UiState.sessionState === "PAUSED" ? T.StyleManager.success : "#1A2534"
                                    border.width: 1; border.color: "#2C3E55"
                                    Text {
                                        anchors.centerIn: parent
                                        text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE SESSION" : "PAUSE TRAJET"
                                        color: S.UiState.sessionState === "PAUSED" ? "#000000" : "#FFFFFF"
                                        font.pixelSize: 13; font.bold: true
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.actionRequested(S.UiState.sessionState === "PAUSED" ? "resume_trip" : "pause_trip")
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; height: 46; radius: 8
                                    color: Qt.rgba(T.StyleManager.danger.r, T.StyleManager.danger.g, T.StyleManager.danger.b, 0.2)
                                    border.width: 1; border.color: T.StyleManager.danger
                                    Text { anchors.centerIn: parent; text: "TERMINER TRAJET"; color: T.StyleManager.danger; font.pixelSize: 13; font.bold: true }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.close()
                                            root.actionRequested("end_trip")
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Compteurs Journaliers Trip A & Trip B
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#121924"
                        border.width: 1.2
                        border.color: "#1F2B3C"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "COMPTEURS KILOMÉTRIQUES"
                                color: T.StyleManager.accent
                                font.family: "Arial, sans-serif"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 100; radius: 10; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 16
                                    Column {
                                        spacing: 4
                                        Text { text: "TRIP A (Court terme)"; color: "#8FA3B8"; font.pixelSize: 12; font.bold: true }
                                        Text { text: S.UiState.fixed(S.UiState.tripA, 1, "0.0") + " km"; color: "#FFFFFF"; font.pixelSize: 26; font.bold: true }
                                    }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        width: 140; height: 42; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                        Text { anchors.centerIn: parent; text: "REMETTRE À 0"; color: "#FFFFFF"; font.pixelSize: 11; font.bold: true }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.close()
                                                root.actionRequested("reset_a")
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 100; radius: 10; color: "#0B0F16"; border.width: 1; border.color: "#1C2737"
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 16
                                    Column {
                                        spacing: 4
                                        Text { text: "TRIP B (Long terme / Conso)"; color: "#8FA3B8"; font.pixelSize: 12; font.bold: true }
                                        Text { text: S.UiState.fixed(S.UiState.tripB, 1, "0.0") + " km · " + S.UiState.fixed(S.UiState.avgConsB, 1, "0.0") + " L/100"; color: "#FFFFFF"; font.pixelSize: 22; font.bold: true }
                                    }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        width: 140; height: 42; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                        Text { anchors.centerIn: parent; text: "REMETTRE À 0"; color: "#FFFFFF"; font.pixelSize: 11; font.bold: true }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.close()
                                                root.actionRequested("reset_b")
                                            }
                                        }
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }

                // -------------------------------------------------------------
                // ONGLET 2 : ACTIONS RAPIDES & COMMANDES SYSTÈME
                // -------------------------------------------------------------
                RowLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 2
                    spacing: 16

                    // Maintenance & Entretien
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#121924"
                        border.width: 1.2
                        border.color: "#1F2B3C"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "MAINTENANCE & SÉCURITÉ"
                                color: T.StyleManager.accent
                                font.family: "Arial, sans-serif"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.16)
                                border.width: 1.5; border.color: T.StyleManager.accent
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "🛠️"; font.pixelSize: 18 }
                                    Text { text: "Menu Maintenance & Protection SD"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.close()
                                        root.actionRequested("maintenance")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: "#182230"; border.width: 1; border.color: "#2C3F58"
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "🔧"; font.pixelSize: 18 }
                                    Text { text: "Valider Révision / Entretien Effectué"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.close()
                                        root.actionRequested("reset_maintenance")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: "#182230"; border.width: 1; border.color: "#2C3F58"
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "🔄"; font.pixelSize: 18 }
                                    Text { text: "Mise à Jour Logicielle Git"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.navigateRequested("system")
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    // Commandes d'Alimentation
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#121924"
                        border.width: 1.2
                        border.color: "#1F2B3C"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "ALIMENTATION DU SYSTÈME"
                                color: T.StyleManager.accent
                                font.family: "Arial, sans-serif"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: "#182230"; border.width: 1; border.color: "#2C3F58"
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "🔄"; font.pixelSize: 18 }
                                    Text { text: "Redémarrer CliOS"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.close()
                                        root.actionRequested("restart")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: Qt.rgba(T.StyleManager.danger.r, T.StyleManager.danger.g, T.StyleManager.danger.b, 0.18)
                                border.width: 1.2; border.color: T.StyleManager.danger
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "🛑"; font.pixelSize: 18 }
                                    Text { text: "Éteindre le Système / Raspberry Pi"; color: T.StyleManager.danger; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.close()
                                        root.actionRequested("shutdown")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 56; radius: 10
                                color: "#182230"; border.width: 1; border.color: "#2C3F58"
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 10
                                    Text { text: "✕"; font.pixelSize: 18; color: "#8FA3B8" }
                                    Text { text: "Quitter l'Application CliOS"; color: "#8FA3B8"; font.pixelSize: 14; font.bold: true }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.close()
                                        root.actionRequested("quit")
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }
    }
}
