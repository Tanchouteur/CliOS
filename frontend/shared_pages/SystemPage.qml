import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()
    signal actionRequested(string action)
    property string logsText: ""
    property string exportPath: ""

    Timer {
        interval: 1000; running: root.visible; repeat: true
        onTriggered: {
            const raw = bridge.getRecentLogs(120)
            const entries = raw ? JSON.parse(raw) : []
            const lines = []
            for (let i = 0; i < entries.length; ++i) {
                const e = entries[i]
                lines.push("[" + e.ts + "] [" + e.level + "] " + e.logger + " — " + e.message)
            }
            root.logsText = lines.join("\n")
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Système"; subtitle: "CliOS " + S.UiState.systemVersion; onBackClicked: root.backRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 150; spacing: 12
            Layout.maximumHeight: 150
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "CPU"; Metric { anchors.centerIn: parent; width: parent.width; label: "Charge application"; value: S.UiState.fixed(S.UiState.appCpuTotalPct, 1, "0,0"); unit: "%"; alignment: Text.AlignHCenter } }
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "RAM"; Metric { anchors.centerIn: parent; width: parent.width; label: "Mémoire application"; value: S.UiState.fixed(S.UiState.appRamMb, 0, "0"); unit: "MB"; alignment: Text.AlignHCenter } }
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Stockage USB"; highlighted: S.UiState.ramMode
                Column { anchors.centerIn: parent; spacing: 5
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.usbConnected ? "PERSISTANT" : "MODE RAM"; color: S.UiState.usbConnected ? T.StyleManager.success : T.StyleManager.danger; font.pixelSize: 25; font.bold: true }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.storageFreeMb, 0, "0") + " MB libres"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                }
            }
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "CAN"; Metric { anchors.centerIn: parent; width: parent.width; label: "Service moteur"; value: S.UiState.serviceHealth.CAN_Moteur ? S.UiState.serviceHealth.CAN_Moteur.status : "—"; alignment: Text.AlignHCenter; valueSize: 26 } }
        }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Journal système"
            ScrollView {
                anchors.fill: parent; clip: true
                TextArea { readOnly: true; text: root.logsText; wrapMode: TextEdit.NoWrap; color: T.StyleManager.textSecondary; font.family: "Monospace"; font.pixelSize: 14; background: null }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 72; spacing: 12
            Button { Layout.fillWidth: true; text: "MAINTENANCE"; primary: true; subtext: "Menu système & OverlayFS"; onClicked: root.actionRequested("maintenance") }
            Button { Layout.fillWidth: true; text: "DIAGNOSTIC"; subtext: root.exportPath ? root.exportPath : "Exporter les logs"; onClicked: root.exportPath = bridge.exportDiagnosticBundle() }
            Button { Layout.fillWidth: true; text: "QUITTER"; onClicked: root.actionRequested("quit") }
            Button { Layout.fillWidth: true; text: "REDÉMARRER"; destructive: true; onClicked: root.actionRequested("restart") }
            Button { Layout.fillWidth: true; text: "ÉTEINDRE"; destructive: true; onClicked: root.actionRequested("shutdown") }
        }
    }
}
