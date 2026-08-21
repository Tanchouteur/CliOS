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
    property string updateChannel: bridge.getUpdateChannel()
    property string pendingUpdateAction: ""
    readonly property var updater: S.UiState.updaterState

    function updaterLabel(state) {
        const labels = {
            "IDLE": "PRÊT", "CHECKING": "RECHERCHE", "AVAILABLE": "DISPONIBLE",
            "DOWNLOADING": "TÉLÉCHARGEMENT", "STAGED": "PRÉPARÉE",
            "ACTIVATING": "ACTIVATION", "UP_TO_DATE": "À JOUR", "ERROR": "ERREUR"
        }
        return labels[state] || state
    }

    ConfirmDialog {
        id: updateConfirm
        z: 100
        title: root.pendingUpdateAction === "activate" ? "Activer la mise à jour ?" : "Revenir à la version stable ?"
        message: (S.UiState.speed > 5 ? "Véhicule en mouvement à " + S.UiState.fixed(S.UiState.speed, 1, "0,0") + " km/h. " : "")
                 + "CliOS va redémarrer. Confirmez explicitement cette opération."
        acceptText: root.pendingUpdateAction === "activate" ? "ACTIVER" : "ROLLBACK"
        onAccepted: {
            visible = false
            if (root.pendingUpdateAction === "activate") bridge.activateUpdate(S.UiState.speed)
            else bridge.rollbackUpdate(S.UiState.speed, root.updateChannel === "beta")
            root.pendingUpdateAction = ""
        }
        onRejected: { visible = false; root.pendingUpdateAction = "" }
    }

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
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Canal de mise à jour"; highlighted: root.updateChannel === "beta"
                RowLayout {
                    anchors.fill: parent; spacing: 8
                    Button {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        text: "STABLE"; subtext: "Recommandé"; primary: root.updateChannel === "stable"
                        onClicked: if (bridge.setUpdateChannel("stable")) root.updateChannel = "stable"
                    }
                    Button {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        text: "BÊTA"; subtext: "Préversions"; destructive: root.updateChannel === "beta"
                        onClicked: if (bridge.setUpdateChannel("beta")) root.updateChannel = "beta"
                    }
                }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 158
            title: "Mise à jour — " + root.updaterLabel(root.updater.state || "IDLE")
            highlighted: root.updater.state === "AVAILABLE" || root.updater.state === "STAGED"
            RowLayout {
                anchors.fill: parent; spacing: 16
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 6
                    Text {
                        Layout.fillWidth: true
                        text: root.updater.available_version ? "Installée " + root.updater.installed_version + "  →  " + root.updater.available_version : "Version installée " + root.updater.installed_version
                        color: T.StyleManager.text; font.pixelSize: 22; font.bold: true
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.updater.message || "Aucune opération en cours"
                        color: root.updater.state === "ERROR" ? T.StyleManager.danger : T.StyleManager.textSecondary
                        font.pixelSize: 16; elide: Text.ElideRight
                    }
                    Progress { Layout.fillWidth: true; value: Number(root.updater.progress || 0); visible: ["CHECKING", "DOWNLOADING", "STAGED", "ACTIVATING"].indexOf(root.updater.state) >= 0 }
                    Text {
                        Layout.fillWidth: true; visible: S.UiState.speed > 5
                        text: "⚠ Véhicule en mouvement : confirmation obligatoire, vitesse journalisée"
                        color: T.StyleManager.danger; font.pixelSize: 15; font.bold: true
                    }
                }
                Button { Layout.preferredWidth: 190; text: "RECHERCHER"; subtext: "Recherche manuelle"; onClicked: bridge.checkForUpdates() }
                Button { Layout.preferredWidth: 190; text: "TÉLÉCHARGER"; primary: true; enabled: root.updater.state === "AVAILABLE"; onClicked: bridge.stageUpdate(S.UiState.speed) }
                Button {
                    Layout.preferredWidth: 170; text: "ACTIVER"; destructive: true
                    enabled: root.updater.state === "STAGED" || root.updater.can_activate === true
                    onClicked: { root.pendingUpdateAction = "activate"; updateConfirm.visible = true }
                }
                Button {
                    Layout.preferredWidth: 170; text: "ROLLBACK"; destructive: true
                    onClicked: { root.pendingUpdateAction = "rollback"; updateConfirm.visible = true }
                }
            }
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
