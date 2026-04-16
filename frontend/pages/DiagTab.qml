import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Item {
    id: root

    // --- Variables d'état ---
    property var codes: bridge.diagnosticCodes !== undefined ? bridge.diagnosticCodes : []
    property bool isScanning: bridge.isScanning !== undefined ? bridge.isScanning : false
    property bool hasScanned: bridge.hasScanned !== undefined ? bridge.hasScanned : false
    property bool hasErrors: codes.length > 0

    property bool isIgnitionOn: bridge.data !== undefined && bridge.data["key_run"]
    property bool isServiceReady: bridge.systemHealth !== undefined &&
                                  bridge.systemHealth["Diag"] !== undefined &&
                                  bridge.systemHealth["Diag"].status !== "ERROR"

    // --- Fonctions de style dynamiques ---
    function getStatusColor() {
        if (!isServiceReady) return "#555555"
        if (!isIgnitionOn) return "#ffaa00"
        if (isScanning) return T.Theme.main
        if (!hasScanned) return "white"
        if (hasErrors) return "#ff4444"
        return "#00cc66"
    }

    function getStatusText() {
        if (!isServiceReady) return "OFFLINE"
        if (!isIgnitionOn) return "CONTACT\nREQUIS"
        if (isScanning) return "SCAN..."
        if (!hasScanned) return "PRÊT"
        if (hasErrors) return codes.length + "\nDÉFAUT(S)"
        return "OK"
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 30

        // panneau de contrôle
        Rectangle {
            Layout.preferredWidth: 350
            Layout.fillHeight: true
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 30
                spacing: 20

                Text {
                    text: "SYSTÈME MOTEUR"
                    color: isServiceReady ? T.Theme.textMain : T.Theme.unselected
                    font.pixelSize: 18
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }

                Item { Layout.fillHeight: true }

                // Indicateur
                Item {
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 160
                    Layout.alignment: Qt.AlignHCenter

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: "transparent"
                        border.width: 4
                        border.color: getStatusColor()

                        opacity: isScanning ? 0.3 : ((isServiceReady && isIgnitionOn) ? 1.0 : 0.3)

                        SequentialAnimation on scale {
                            running: isScanning
                            loops: Animation.Infinite
                            NumberAnimation { from: 1.0; to: 1.1; duration: 800; easing.type: Easing.OutQuad }
                            NumberAnimation { from: 1.1; to: 1.0; duration: 800; easing.type: Easing.InQuad }
                        }
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: 130; height: 130; radius: 65
                        color: Qt.rgba(getStatusColor().r, getStatusColor().g, getStatusColor().b, 0.15)
                        border.color: getStatusColor()
                        border.width: 2

                        Text {
                            anchors.centerIn: parent
                            text: getStatusText()
                            color: getStatusColor()
                            font.pixelSize: (!hasScanned || isScanning || !hasErrors || !isIgnitionOn) ? 20 : 24
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                // Texte de status dynamique
                Text {
                    text: {
                        if (!isServiceReady) return "Interface CAN non disponible."
                        if (!isIgnitionOn) return "Tournez la clé (Cran 2) pour scanner."
                        if (isScanning) return "Interrogation de l'ECU..."
                        if (!hasScanned) return "En attente de diagnostic."
                        if (hasErrors) return "Anomalies détectées."
                        return "Aucun défaut, système sain."
                    }
                    color: T.Theme.unselected
                    font.pixelSize: 14
                    Layout.alignment: Qt.AlignHCenter
                }

                Item { Layout.fillHeight: true }

                // Boutons d'action
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 15

                    // Bouton
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 50
                        radius: 8

                        color: (!isServiceReady || !isIgnitionOn || isScanning) ? T.Theme.bgMain : T.Theme.main
                        opacity: (!isServiceReady || !isIgnitionOn || isScanning) ? 0.5 : (btnScanArea.pressed ? 0.8 : 1.0)

                        Text {
                            anchors.centerIn: parent
                            text: isScanning ? "ANALYSE EN COURS..." : "LANCER LE DIAGNOSTIC"
                            color: (isServiceReady && isIgnitionOn) ? "white" : T.Theme.unselected
                            font.bold: true
                        }

                        MouseArea {
                            id: btnScanArea
                            anchors.fill: parent
                            enabled: isServiceReady && isIgnitionOn && !isScanning
                            cursorShape: Qt.PointingHandCursor
                            onClicked: bridge.requestDiagnosticScan()
                        }
                    }

                    // Bouton CLEAR
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 50
                        radius: 8
                        color: "transparent"
                        border.color: (isServiceReady && isIgnitionOn && hasErrors) ? "#ff4444" : Qt.rgba(1,1,1,0.1)
                        border.width: 2
                        opacity: (isServiceReady && isIgnitionOn && hasErrors) ? (btnClearArea.pressed ? 0.5 : 1.0) : 0.3

                        Text {
                            anchors.centerIn: parent
                            text: "EFFACER LES DÉFAUTS"
                            color: (isServiceReady && isIgnitionOn && hasErrors) ? "#ff4444" : T.Theme.unselected
                            font.bold: true
                        }

                        MouseArea {
                            id: btnClearArea
                            anchors.fill: parent
                            enabled: isServiceReady && isIgnitionOn && hasErrors && !isScanning
                            cursorShape: Qt.PointingHandCursor
                            onClicked: console.log("Demande d'effacement")
                        }
                    }
                }
            }
        }

        // rapport
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)
            clip: true

            // etat 1
            Column {
                anchors.centerIn: parent
                visible: !hasScanned && !isScanning
                spacing: 15

                Text { text: "🔍"; font.pixelSize: 50; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    text: "Prêt pour le diagnostic"
                    color: "white"; font.pixelSize: 20; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Mettez le contact et lancez l'analyse pour interroger\nle calculateur moteur de votre véhicule."
                    color: T.Theme.unselected; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; anchors.horizontalCenter: parent.horizontalCenter
                }
            }

            // etat 2
            Column {
                anchors.centerIn: parent
                visible: hasScanned && !hasErrors && !isScanning
                spacing: 15

                Text { text: "✓"; color: "#00cc66"; font.pixelSize: 60; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    text: "La valise n'a trouvé aucun code d'erreur."
                    color: T.Theme.unselected; font.pixelSize: 16; anchors.horizontalCenter: parent.horizontalCenter
                }
            }

            // etat 3
            ListView {
                id: dtcList
                anchors.fill: parent
                anchors.margins: 20
                visible: hasErrors && !isScanning
                spacing: 15
                model: root.codes

                delegate: Rectangle {
                    width: dtcList.width; height: 80
                    color: Qt.rgba(1, 0, 0, 0.05)
                    border.color: Qt.rgba(1, 0, 0, 0.2); border.width: 1
                    radius: 8

                    RowLayout {
                        anchors.fill: parent; anchors.margins: 15; spacing: 20
                        Text {
                            text: modelData
                            color: T.theme.danger; font.pixelSize: 28; font.bold: true; Layout.alignment: Qt.AlignVCenter
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; spacing: 4
                            Text { text: "Défaut Système Détecté"; color: "white"; font.pixelSize: 16; font.bold: true }
                            Text { text: "Une anomalie a été enregistrée par l'ECU."; color: T.Theme.unselected; font.pixelSize: 14 }
                        }
                    }
                }
            }
        }
    }
}