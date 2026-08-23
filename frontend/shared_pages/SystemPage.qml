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
    property double currentEpoch: Date.now() / 1000
    readonly property var updater: S.UiState.updaterState
    readonly property var updateError: root.updater.error || ({})

    function elapsedSeconds() {
        const started = Number(root.updater.started_at || 0)
        if (started <= 0 || ["CHECKING", "DOWNLOADING", "ACTIVATING"].indexOf(root.updater.state) < 0) return 0
        return Math.max(0, Math.floor(root.currentEpoch - started))
    }

    function updaterLabel(state) {
        const labels = {
            "IDLE": "PRÊT", "CHECKING": "RECHERCHE", "AVAILABLE": "DISPONIBLE",
            "DOWNLOADING": "TÉLÉCHARGEMENT", "STAGED": "PRÉPARÉE",
            "ACTIVATING": "ACTIVATION", "UP_TO_DATE": "À JOUR", "ERROR": "ERREUR"
        }
        return labels[state] || state
    }

    function phaseLabel(phase) {
        const labels = {
            "idle": "attente", "catalog": "catalogue GitHub", "request": "transmission au helper",
            "manifest": "manifeste", "signature": "signature", "archive": "archive",
            "hash": "contrôle SHA-256", "extract": "extraction", "environment": "environnement Python",
            "self_check": "auto-vérification", "precompile": "précompilation", "complete": "terminé",
            "activate": "activation", "rollback": "retour arrière"
        }
        return labels[phase] || phase
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
            root.currentEpoch = Date.now() / 1000
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
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Stockage"; highlighted: S.UiState.ramMode
                Column { anchors.centerIn: parent; spacing: 5
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.usbConnected ? "CLÉ USB" : (S.UiState.internalStorage ? "CARTE SD" : "MODE RAM"); color: S.UiState.usbConnected ? T.StyleManager.success : (S.UiState.internalStorage ? T.StyleManager.warning : T.StyleManager.danger); font.pixelSize: 25; font.bold: true }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.storageFreeMb, 0, "0") + " MB libres"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.usbConnected ? S.UiState.storageMount : (S.UiState.storageDiagnostic || S.UiState.storageMode); color: T.StyleManager.textSecondary; font.pixelSize: 11; elide: Text.ElideRight; width: 250; horizontalAlignment: Text.AlignHCenter }
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
            Layout.fillWidth: true; Layout.preferredHeight: 196
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
                        font.pixelSize: 16; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                    }
                    Progress { Layout.fillWidth: true; value: Number(root.updater.progress || 0); visible: ["CHECKING", "DOWNLOADING", "STAGED", "ACTIVATING"].indexOf(root.updater.state) >= 0 }
                    Text {
                        Layout.fillWidth: true
                        visible: !!root.updater.detail || root.elapsedSeconds() > 0
                        text: (root.updater.phase ? "Étape " + root.phaseLabel(root.updater.phase) + " • " : "")
                              + Math.round(Number(root.updater.progress || 0)) + "%"
                              + (root.elapsedSeconds() > 0 ? " • " + root.elapsedSeconds() + " s écoulées" : "")
                              + (root.updater.detail ? " — " + root.updater.detail : "")
                        color: T.StyleManager.textSecondary; font.pixelSize: 13
                        wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true; visible: root.updater.state === "ERROR" && !!root.updateError.code
                        text: "Code " + (root.updateError.code || "") + (root.updateError.phase ? " • phase " + root.updateError.phase : "")
                        color: T.StyleManager.warning; font.pixelSize: 12; font.family: T.StyleManager.fontMono
                    }
                    Text {
                        Layout.fillWidth: true; visible: S.UiState.speed > 5
                        text: "⚠ Véhicule en mouvement : confirmation obligatoire, vitesse journalisée"
                        color: T.StyleManager.danger; font.pixelSize: 15; font.bold: true
                    }
                }
                Button { Layout.preferredWidth: 190; text: "RECHERCHER"; subtext: "Recherche manuelle"; onClicked: bridge.checkForUpdates() }
                Button { Layout.preferredWidth: 190; text: "TÉLÉCHARGER"; primary: true; enabled: root.updater.state === "AVAILABLE" && !!root.updater.available_version; onClicked: bridge.stageUpdate(S.UiState.speed) }
                Button {
                    Layout.preferredWidth: 170; text: "ACTIVER"; destructive: true
                    enabled: root.updater.state === "STAGED" || root.updater.can_activate === true
                    onClicked: { root.pendingUpdateAction = "activate"; updateConfirm.visible = true }
                }
                Button {
                    Layout.preferredWidth: 190; text: "ROLLBACK"; destructive: true
                    subtext: root.updater.can_rollback ? ("Vers " + root.updater.rollback_target) : "Aucune version précédente"
                    enabled: root.updater.can_rollback === true
                    onClicked: { root.pendingUpdateAction = "rollback"; updateConfirm.visible = true }
                }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Journal système"
            ScrollView {
                anchors.fill: parent; clip: true
                TextArea { readOnly: true; text: root.logsText; wrapMode: TextEdit.NoWrap; color: T.StyleManager.textSecondary; font.family: T.StyleManager.fontMono; font.pixelSize: 14; background: null }
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
