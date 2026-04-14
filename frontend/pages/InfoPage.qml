import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T
import "../components" as C

Item {
    id: root
    anchors.fill: parent

    // --- LIAISON AVEC LE PYTHON ---
    property real cpuUsage: bridge.data !== undefined && bridge.data.app_cpu_total_pct !== undefined ? bridge.data.app_cpu_total_pct : 0.0
    property real ramUsage: bridge.data !== undefined && bridge.data.app_ram_mb !== undefined ? bridge.data.app_ram_mb : 0.0

    // Définition de seuils pour colorer les barres en rouge si danger
    property color cpuColor: cpuUsage > 80.0 ? T.Theme.danger : T.Theme.main
    property color ramColor: ramUsage > 800.0 ? T.Theme.danger : T.Theme.main // Exemple: Alerte à 800MB

    // --- EN-TÊTE ---
    C.PageHeader {
        id: header
        title: "INFORMATIONS SYSTÈME"
        onBackClicked: {
            root.StackView.view.pop()

        }
    }

    // --- CONTENU PRINCIPAL ---
    GridLayout {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 30
        anchors.topMargin: 20

        columns: 2
        rowSpacing: 20
        columnSpacing: 20

        // ==========================================
        // CARTE 1 : CPU
        // ==========================================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            color: T.Theme.bgDimmed
            radius: 12
            border.color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 15

                Text { text: "PROCESSEUR (CPU)"; color: T.Theme.unselected; font.pixelSize: 16; font.bold: true }

                RowLayout {
                    width: parent.width
                    Text {
                        text: root.cpuUsage.toFixed(1) + " %"
                        color: T.Theme.textMain; font.pixelSize: 42; font.bold: true
                        Layout.preferredWidth: 120
                    }

                    // Barre de progression custom
                    Rectangle {
                        Layout.fillWidth: true
                        height: 12
                        radius: 6
                        color: Qt.rgba(0, 0, 0, 0.4)

                        Rectangle {
                            width: parent.width * (Math.min(root.cpuUsage, 100) / 100.0)
                            height: parent.height
                            radius: 6
                            color: root.cpuColor
                            Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                            Behavior on color { ColorAnimation { duration: 300 } }
                        }
                    }
                }
            }
        }

        // ==========================================
        // CARTE 2 : RAM
        // ==========================================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            color: T.Theme.bgDimmed
            radius: 12
            border.color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 15

                Text { text: "MÉMOIRE VIVE (RAM)"; color: T.Theme.unselected; font.pixelSize: 16; font.bold: true }

                RowLayout {
                    width: parent.width
                    Text {
                        text: root.ramUsage.toFixed(0) + " MB"
                        color: T.Theme.textMain; font.pixelSize: 42; font.bold: true
                        Layout.preferredWidth: 150
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 12
                        radius: 6
                        color: Qt.rgba(0, 0, 0, 0.4)

                        Rectangle {
                            // On base le 100% sur 1024 MB (1 GB) pour l'affichage visuel
                            width: parent.width * (Math.min(root.ramUsage, 1024) / 1024.0)
                            height: parent.height
                            radius: 6
                            color: root.ramColor
                            Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                            Behavior on color { ColorAnimation { duration: 300 } }
                        }
                    }
                }
            }
        }

        // ==========================================
        // CARTE 3 : LOGICIEL & VÉHICULE
        // ==========================================
        Rectangle {
            Layout.columnSpan: 2 // Prend toute la largeur en bas
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: T.Theme.bgDimmed
            radius: 12
            border.color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 10

                Text { text: "INFORMATIONS LOGICIELLES"; color: T.Theme.unselected; font.pixelSize: 16; font.bold: true }

                Item { Layout.preferredHeight: 10 } // Espaceur

                GridLayout {
                    columns: 2
                    columnSpacing: 60
                    rowSpacing: 15

                    Text {
                        text: "Version de l'Interface :"
                        color: T.Theme.unselected
                        font.pixelSize: 20
                    }
                    Text {
                        // Utilisation dynamique de la donnee injectee par le backend
                        text: bridge.data !== undefined && bridge.data.system_version !== undefined ? "ClOS v" + bridge.data.system_version : "ClOS v?.?.?"
                        color: T.Theme.textMain
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text { text: "Moteur Physique :"; color: T.Theme.unselected; font.pixelSize: 20 }
                    Text { text: "Actif (Mock GT3)"; color: T.Theme.main; font.pixelSize: 20; font.bold: true }

                    Text { text: "Connexion CAN Bus :"; color: T.Theme.unselected; font.pixelSize: 20 }
                    Text { text: "Déconnecté"; color: T.Theme.danger; font.pixelSize: 20; font.bold: true }
                }

                Item { Layout.fillHeight: true } // Pousse tout vers le haut
            }
        }
    }
}