import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
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
        GtPageHeader { Layout.fillWidth: true; title: "Système"; subtitle: "CliOS " + (S.UiState.vehicle.system_version || "—"); onBackClicked: root.backRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 150; spacing: 12
            Layout.maximumHeight: 150
            GtCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "CPU"; GtMetric { anchors.centerIn: parent; width: parent.width; label: "Charge application"; value: S.UiState.fixed(S.UiState.vehicle.app_cpu_total_pct, 1, "0,0"); unit: "%"; alignment: Text.AlignHCenter } }
            GtCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "RAM"; GtMetric { anchors.centerIn: parent; width: parent.width; label: "Mémoire application"; value: S.UiState.fixed(S.UiState.vehicle.app_ram_mb, 0, "0"); unit: "MB"; alignment: Text.AlignHCenter } }
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Stockage USB"; highlighted: S.UiState.ramMode
                Column { anchors.centerIn: parent; spacing: 5
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.usbConnected ? "PERSISTANT" : "MODE RAM"; color: S.UiState.usbConnected ? T.StyleManager.success : T.StyleManager.danger; font.pixelSize: 25; font.bold: true }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.storage.free_space_mb, 0, "0") + " MB libres"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                }
            }
            GtCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "CAN"; GtMetric { anchors.centerIn: parent; width: parent.width; label: "Service moteur"; value: S.UiState.health.CAN_Moteur ? S.UiState.health.CAN_Moteur.status : "—"; alignment: Text.AlignHCenter; valueSize: 26 } }
        }
        GtCard {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Journal système"
            ScrollView {
                anchors.fill: parent; clip: true
                TextArea { readOnly: true; text: root.logsText; wrapMode: TextEdit.NoWrap; color: T.StyleManager.textSecondary; font.family: "Monospace"; font.pixelSize: 14; background: null }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 72; spacing: 12
            GtButton { Layout.fillWidth: true; text: "EXPORTER LE DIAGNOSTIC"; primary: true; subtext: root.exportPath ? root.exportPath : "Logs, configuration et santé"; onClicked: root.exportPath = bridge.exportDiagnosticBundle() }
            GtButton { Layout.fillWidth: true; text: "QUITTER CLIOS"; onClicked: root.actionRequested("quit") }
            GtButton { Layout.fillWidth: true; text: "REDÉMARRER"; destructive: true; onClicked: root.actionRequested("restart") }
            GtButton { Layout.fillWidth: true; text: "ÉTEINDRE"; destructive: true; onClicked: root.actionRequested("shutdown") }
        }
    }
}
