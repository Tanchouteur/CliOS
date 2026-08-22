import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()
    readonly property var codes: S.UiState.diagnosticCodes
    readonly property bool scanning: S.UiState.isScanning
    readonly property bool scanned: S.UiState.hasScanned
    readonly property bool ready: S.UiState.serviceHealth.Diag === undefined || S.UiState.serviceHealth.Diag.status !== "ERROR"
    readonly property string statusText: !ready ? "INDISPONIBLE" : scanning ? "ANALYSE" : !scanned ? "PRÊT" : codes.length ? "DÉFAUTS" : "OK"
    readonly property color statusColor: !ready ? T.StyleManager.textSecondary : scanning ? T.StyleManager.accent : codes.length ? T.StyleManager.danger : scanned ? T.StyleManager.success : T.StyleManager.text

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        PageHeader {
            Layout.fillWidth: true
            title: "Diagnostic moteur"
            subtitle: "Lecture des codes défaut OBD-II"
            onBackClicked: root.backRequested()
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            Card {
            Layout.preferredWidth: 350; Layout.fillHeight: true; title: "Diagnostic moteur"; highlighted: root.codes.length > 0
            ColumnLayout {
                anchors.fill: parent; spacing: 20
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 180; height: 180; radius: 90
                    color: Qt.rgba(root.statusColor.r, root.statusColor.g, root.statusColor.b, 0.12)
                    border.width: 3; border.color: root.statusColor
                    Text { anchors.centerIn: parent; text: root.statusText; color: root.statusColor; font.pixelSize: 25; font.bold: true }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.scanning ? "Interrogation de l’ECU en cours" : root.codes.length ? root.codes.length + " code(s) enregistré(s)" : root.scanned ? "Aucun défaut détecté" : "Prêt à interroger le calculateur"
                    color: T.StyleManager.textSecondary; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                }
                Item { Layout.fillHeight: true }
                Button { Layout.fillWidth: true; text: root.scanning ? "ANALYSE EN COURS" : "LANCER LE SCAN"; primary: true; enabled: root.ready && !root.scanning; onClicked: bridge.requestDiagnosticScan() }
                Button { Layout.fillWidth: true; text: "EFFACER LES DÉFAUTS"; destructive: true; enabled: false; subtext: "Backend non disponible" }
            }
        }
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Rapport DTC"
                ListView {
                anchors.fill: parent; clip: true; spacing: 10; model: root.codes
                delegate: Rectangle {
                    width: ListView.view.width; height: 84; radius: T.StyleManager.radiusSmall
                    color: T.StyleManager.surfaceRaised; border.width: 1; border.color: T.StyleManager.danger
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 20
                        Text { text: String(modelData); color: T.StyleManager.danger; font.pixelSize: 29; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: "Défaut mémorisé par le calculateur moteur"; color: T.StyleManager.textSecondary; font.pixelSize: 18 }
                    }
                }
                Text {
                    anchors.centerIn: parent; visible: root.codes.length === 0
                    text: root.scanning ? "Analyse en cours…" : root.scanned ? "Aucun code défaut" : "Lancez un scan pour afficher les codes DTC"
                    color: root.scanned ? T.StyleManager.success : T.StyleManager.textSecondary
                    font.pixelSize: 23
                }
                }
            }
        }
    }
}
