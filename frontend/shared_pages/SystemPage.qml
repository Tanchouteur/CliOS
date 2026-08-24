import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    objectName: "systemSettingsPage"
    property string initialRoute: "system"
    property int tab: initialRoute === "maintenance" || initialRoute === "storage" ? 2 : (initialRoute === "updates" ? 1 : (initialRoute === "power" ? 3 : 0))
    property string updateChannel: bridge.getUpdateChannel()
    readonly property var tabs: ["RÉSEAU", "MISES À JOUR", "STOCKAGE", "ALIMENTATION"]
    readonly property var network: S.UiState.networkState
    readonly property var maintenance: S.UiState.maintenanceState
    readonly property var updater: S.UiState.updaterState
    readonly property var updateError: updater.error || ({})
    readonly property bool vehicleMoving: S.UiState.speed > 5
    readonly property var updaterLabels: ({
        "IDLE":"PRÊT", "CHECKING":"RECHERCHE", "AVAILABLE":"DISPONIBLE",
        "DOWNLOADING":"TÉLÉCHARGEMENT", "STAGED":"PRÉPARÉE", "ACTIVATING":"ACTIVATION",
        "UP_TO_DATE":"À JOUR", "ERROR":"ERREUR"
    })
    signal actionRequested(string action)
    signal backRequested()
    onInitialRouteChanged: tab = initialRoute === "maintenance" || initialRoute === "storage" ? 2 : (initialRoute === "updates" ? 1 : (initialRoute === "power" ? 3 : 0))
    function elapsedSeconds() {
        const started = Number(updater.started_at || 0)
        return started > 0 ? Math.max(0, Math.floor(Date.now()/1000-started)) : 0
    }
    // Les actions bridge.activateUpdate / bridge.rollbackUpdate sont routées
    // vers l'unique ConfirmDialog global de AppShell.

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Système"; subtitle: "Réseau, logiciel, stockage et alimentation"; showBack: false }
        RowLayout { Layout.fillWidth: true; Layout.minimumHeight: 64; Layout.preferredHeight: 64; Layout.maximumHeight: 64; spacing: 10
            Repeater { model: root.tabs; Button { Layout.fillWidth: true; Layout.minimumHeight: 56; Layout.maximumHeight: 64; text: modelData; primary: root.tab === index; onClicked: root.tab = index } }
        }
        Item { Layout.fillWidth: true; Layout.fillHeight: true
            RowLayout { anchors.fill: parent; visible: root.tab === 0; spacing: 14
                Card { Layout.preferredWidth: 410; Layout.fillHeight: true; title: "Connexion active"; highlighted: !!root.network.active_ssid
                    ColumnLayout { anchors.fill: parent; spacing: 14
                        Text { Layout.fillWidth: true; text: root.network.available === false ? "NETWORKMANAGER INDISPONIBLE" : (root.network.active_ssid || "HORS LIGNE"); color: root.network.active_ssid ? T.StyleManager.success : T.StyleManager.warning; font.pixelSize: 25; font.bold: true; wrapMode: Text.WordWrap }
                        Text { Layout.fillWidth: true; text: root.network.ip_address ? "Adresse IP  " + root.network.ip_address : "Aucune adresse IP"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                        Text { Layout.fillWidth: true; visible: !!root.network.error; text: root.network.error || ""; color: T.StyleManager.danger; font.pixelSize: 15; wrapMode: Text.WordWrap }
                        RowLayout { Layout.fillWidth: true
                            Text { Layout.fillWidth: true; text: "Radio Wi-Fi"; color: T.StyleManager.text; font.pixelSize: 18 }
                            Toggle { checked: root.network.wifi_enabled === true; enabled: root.network.available !== false && !root.network.busy; onToggled: value => root.actionRequested("wifi_radio:" + (value ? "on" : "off")) }
                        }
                        Item { Layout.fillHeight: true }
                        Button { Layout.fillWidth: true; text: root.network.busy ? "OPÉRATION EN COURS" : "ACTUALISER"; primary: true; enabled: !root.network.busy; onClicked: root.actionRequested("wifi_refresh") }
                        Button { Layout.fillWidth: true; text: "DÉCONNECTER"; enabled: !!root.network.active_ssid && !root.network.busy; onClicked: root.actionRequested("wifi_disconnect") }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Réseaux mémorisés à portée"
                    ListView { anchors.fill: parent; clip: true; spacing: 10; model: root.network.saved_networks || []
                        delegate: Button { width: ListView.view.width; height: 72; text: modelData.name || modelData.ssid; subtext: modelData.active ? "Connecté · " + modelData.signal + "%" : (modelData.available ? "Disponible · " + modelData.signal + "%" : "Hors de portée"); primary: modelData.active; enabled: modelData.available && !modelData.active && !root.network.busy; onClicked: root.actionRequested("wifi_connect:" + modelData.uuid) }
                        Text { anchors.centerIn: parent; visible: (root.network.saved_networks || []).length === 0; text: "Aucun profil Wi-Fi mémorisé à afficher"; color: T.StyleManager.textSecondary; font.pixelSize: 20 }
                    }
                }
            }
            ColumnLayout { anchors.fill: parent; visible: root.tab === 1; spacing: 14
                Card { Layout.fillWidth: true; Layout.preferredHeight: 150; title: "Version et canal"
                    RowLayout { anchors.fill: parent; spacing: 12
                        Metric { Layout.fillWidth: true; label: "Installée"; value: root.updater.installed_version || S.UiState.systemVersion; alignment: Text.AlignHCenter; valueSize: 27 }
                        Button { Layout.preferredWidth: 220; text: "STABLE"; primary: root.updateChannel === "stable"; onClicked: if (bridge.setUpdateChannel("stable")) root.updateChannel="stable" }
                        Button { Layout.preferredWidth: 220; text: "BÊTA"; primary: root.updateChannel === "beta"; onClicked: if (bridge.setUpdateChannel("beta")) root.updateChannel="beta" }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Mise à jour · " + (root.updaterLabels[root.updater.state] || root.updater.state || "IDLE"); highlighted: root.updater.state === "AVAILABLE" || root.updater.state === "STAGED"
                    ColumnLayout { anchors.fill: parent; spacing: 12
                        Text { Layout.fillWidth: true; text: root.updater.message || "Aucune opération en cours"; color: root.updater.state === "ERROR" ? T.StyleManager.danger : T.StyleManager.text; font.pixelSize: 20; wrapMode: Text.WordWrap }
                        Progress { Layout.fillWidth: true; value: Number(root.updater.progress || 0); indeterminate: root.updater.indeterminate === true; visible: ["CHECKING","DOWNLOADING","STAGED","ACTIVATING"].indexOf(root.updater.state) >= 0 }
                        Text { Layout.fillWidth: true; visible: Number(root.updater.bytes_received || 0) > 0; text: Math.round(Number(root.updater.bytes_received || 0) / 1048576 * 10) / 10 + " MB reçus" + (Number(root.updater.bytes_total || 0) > 0 ? " / " + (Math.round(Number(root.updater.bytes_total || 0) / 1048576 * 10) / 10) + " MB" : ""); color: T.StyleManager.textSecondary; font.pixelSize: 14 }
                        Text { Layout.fillWidth: true; text: root.updater.detail || (root.updateError.phase ? "Erreur pendant " + root.updateError.phase : "Version disponible : " + (root.updater.available_version || "—")); color: T.StyleManager.textSecondary; font.pixelSize: 15; wrapMode: Text.WordWrap }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; Layout.preferredHeight: 72; spacing: 12
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "RECHERCHER"; onClicked: bridge.checkForUpdates() }
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "TÉLÉCHARGER"; primary: true; enabled: root.updater.state === "AVAILABLE"; onClicked: bridge.stageUpdate(S.UiState.speed) }
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "ACTIVER"; destructive: true; enabled: root.updater.state === "STAGED" || root.updater.can_activate === true; onClicked: root.actionRequested("update_activate") }
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "RETOUR ARRIÈRE"; subtext: root.updater.rollback_target || "Version précédente"; destructive: true; enabled: root.updater.can_rollback === true; onClicked: root.actionRequested("update_rollback") }
                        }
                    }
                }
            }
            RowLayout { anchors.fill: parent; visible: root.tab === 2; spacing: 14
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Données CliOS"
                    ColumnLayout { anchors.fill: parent; spacing: 14
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: S.UiState.usbConnected ? "Clé USB connectée" : (S.UiState.internalStorage ? "Carte SD interne" : "Mode mémoire volatile"); value: S.UiState.fixed(S.UiState.storageFreeMb, 0, "—"); unit: "MB libres"; alignment: Text.AlignHCenter; valueSize: 42 }
                        Text { Layout.fillWidth: true; text: S.UiState.storageMount || S.UiState.storageDiagnostic || S.UiState.storageMode; color: T.StyleManager.textSecondary; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideMiddle }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Protection de la carte SD"; highlighted: root.maintenance.restart_required === true
                    ColumnLayout { anchors.fill: parent; spacing: 16
                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: "État actuel"; color: T.StyleManager.textSecondary; font.pixelSize: 17 } Text { text: root.maintenance.overlay_current ? "PROTÉGÉE" : "LECTURE / ÉCRITURE"; color: root.maintenance.overlay_current ? T.StyleManager.success : T.StyleManager.warning; font.pixelSize: 19; font.bold: true } }
                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: "État configuré"; color: T.StyleManager.textSecondary; font.pixelSize: 17 } Text { text: root.maintenance.overlay_configured ? "PROTÉGÉE" : "LECTURE / ÉCRITURE"; color: root.maintenance.overlay_configured ? T.StyleManager.success : T.StyleManager.warning; font.pixelSize: 19; font.bold: true } }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: T.StyleManager.radiusSmall; color: root.maintenance.restart_required ? T.StyleManager.accentSoft : T.StyleManager.surfaceSoft
                            Text { anchors.centerIn: parent; text: root.maintenance.restart_required ? "REDÉMARRAGE REQUIS POUR APPLIQUER" : "CONFIGURATION APPLIQUÉE"; color: root.maintenance.restart_required ? T.StyleManager.warning : T.StyleManager.success; font.pixelSize: 17; font.bold: true }
                        }
                        Item { Layout.fillHeight: true }
                        Button { Layout.fillWidth: true; text: root.maintenance.overlay_busy ? "MODIFICATION EN COURS" : "MODIFIER LA PROTECTION"; destructive: true; enabled: !root.maintenance.overlay_busy && !root.maintenance.restart_required; onClicked: root.actionRequested("toggle_overlayfs") }
                    }
                }
            }
            GridLayout { anchors.fill: parent; visible: root.tab === 3; columns: 2; rowSpacing: 14; columnSpacing: 14
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "QUITTER CLIOS"; subtext: "Fermer l’application"; onClicked: root.actionRequested("quit") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "RELANCER CLIOS"; subtext: "Recharger le cockpit et les services"; destructive: true; onClicked: root.actionRequested("restart") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "REDÉMARRER LE SYSTÈME"; subtext: "Redémarrer le Raspberry Pi"; destructive: true; onClicked: root.actionRequested("reboot") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "ÉTEINDRE LE SYSTÈME"; subtext: "Arrêt complet"; destructive: true; onClicked: root.actionRequested("shutdown") }
            }
        }
    }
}
