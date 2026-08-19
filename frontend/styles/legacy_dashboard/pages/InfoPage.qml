import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../style" as T
import "../components" as C
import "../../../state" as S

Item {
    id: root
    anchors.fill: parent

    // Données système exposées par le bridge.
    property real cpuUsage: S.UiState.appCpuTotalPct
    property real ramUsage: S.UiState.appRamMb

    // Seuils visuels d'alerte.
    property color cpuColor: cpuUsage > 80.0 ? T.Theme.danger : T.Theme.main
    property color ramColor: ramUsage > 800.0 ? T.Theme.danger : T.Theme.main

    property var health: S.UiState.serviceHealth
    property var storageStatus: S.UiState.storageState


    // En-tête.
    C.PageHeader {
        id: header
        title: "INFORMATIONS SYSTÈME"
        onBackClicked: {
            root.StackView.view.pop()

        }
    }

    // Contenu principal.
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

        // Carte CPU.
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
                    spacing: 20
                    Text {
                        text: root.cpuUsage.toFixed(1) + " %"
                        color: T.Theme.textMain; font.pixelSize: 42; font.bold: true
                        Layout.minimumWidth: 160
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 12
                        radius: 6
                        color: Qt.rgba(0, 0, 0, 0.4)
                        clip: true

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

        // Carte RAM.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            color: T.Theme.bgDimmed
            radius: 12
            border.color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 1

            // Plafond RAM dynamique pour l'échelle de la jauge.
            property real ramMax: Math.max(1024, Math.ceil(root.ramUsage / 512) * 512)

            Column {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 15

                RowLayout {
                    width: parent.width
                    Text { text: "MÉMOIRE VIVE (RAM)"; color: T.Theme.unselected; font.pixelSize: 16; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text { text: "Max: " + parent.parent.ramMax + " MB"; color: T.Theme.unselected; font.pixelSize: 12 }
                }

                RowLayout {
                    width: parent.width
                    spacing: 20
                    Text {
                        text: root.ramUsage.toFixed(0) + " MB"
                        color: T.Theme.textMain; font.pixelSize: 42; font.bold: true
                        Layout.minimumWidth: 160
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 12
                        radius: 6
                        color: Qt.rgba(0, 0, 0, 0.4)
                        clip: true

                        Rectangle {
                            width: parent.width * (Math.min(root.ramUsage, parent.parent.parent.ramMax) / parent.parent.parent.ramMax)
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

        // Carte informations logicielles.
        Rectangle {
            Layout.columnSpan: 2
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

                Item { Layout.preferredHeight: 10 }

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
                        text: "CliOS v" + S.UiState.systemVersion
                        color: T.Theme.textMain
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text { text: "Connexion CAN Bus :"; color: T.Theme.unselected; font.pixelSize: 20 }
                    Text { text: ""; color: T.Theme.danger; font.pixelSize: 20; font.bold: true }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: Qt.rgba(1, 1, 1, 0.08)
                }

                Text { text: "STOCKAGE"; color: T.Theme.unselected; font.pixelSize: 16; font.bold: true }

                GridLayout {
                    columns: 4
                    columnSpacing: 25
                    rowSpacing: 10

                    Text { text: "Mode :"; color: T.Theme.unselected; font.pixelSize: 17 }
                    Text {
                        text: root.storageStatus.usb_connected === true ? "USB" : "DÉGRADÉ (RAM)"
                        color: root.storageStatus.usb_connected === true ? T.Theme.main : T.Theme.danger
                        font.pixelSize: 17; font.bold: true
                    }
                    Text { text: "Espace libre :"; color: T.Theme.unselected; font.pixelSize: 17 }
                    Text {
                        text: root.storageStatus.usb_connected === true
                              ? ((root.storageStatus.free_space_mb || 0) / 1024).toFixed(1) + " GB"
                              : "Non persistant"
                        color: T.Theme.textMain; font.pixelSize: 17; font.bold: true
                    }

                    Text { text: "Point de montage :"; color: T.Theme.unselected; font.pixelSize: 17 }
                    Text {
                        text: root.storageStatus.mount_point || "—"
                        color: T.Theme.textMain; font.pixelSize: 17; font.bold: true
                    }
                    Text { text: "Trajets sauvegardés :"; color: T.Theme.unselected; font.pixelSize: 17 }
                    Text {
                        text: root.storageStatus.trip_count !== undefined ? root.storageStatus.trip_count : 0
                        color: T.Theme.textMain; font.pixelSize: 17; font.bold: true
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
