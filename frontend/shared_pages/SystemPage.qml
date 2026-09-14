import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QC
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
    property string networkListMode: "available"
    property string selectedSsid: ""
    property string selectedUuid: ""
    property bool selectedSecured: false
    property string networkDialogMode: ""
    property bool keyboardShift: false
    property bool showWifiPassword: false
    readonly property var wifiKeys: [
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
        "a", "z", "e", "r", "t", "y", "u", "i", "o", "p",
        "q", "s", "d", "f", "g", "h", "j", "k", "l", "m",
        "w", "x", "c", "v", "b", "n", "-", "_", ".", "@",
        "!", "?", "#", "$", "%", "&", "+", "=", "/", ":"
    ]
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
    function openNetwork(ssid, secured) {
        selectedSsid = ssid
        selectedSecured = secured
        networkDialogMode = secured ? "password" : ""
        if (!secured) actionRequested("wifi_add:" + encodeURIComponent(ssid) + ":")
    }
    function confirmForget(uuid, ssid) {
        selectedUuid = uuid
        selectedSsid = ssid
        networkDialogMode = "forget"
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
                Card { Layout.preferredWidth: 410; Layout.fillHeight: true; title: "Connexion active"; highlighted: !!root.network.active_ssid || root.network.connectivity === "full"
                    ColumnLayout { anchors.fill: parent; spacing: 14
                        Text { Layout.fillWidth: true; text: root.network.available === false ? "NETWORKMANAGER INDISPONIBLE" : (root.network.active_ssid || (root.network.connectivity === "full" ? "ETHERNET / INTERNET" : "HORS LIGNE")); color: root.network.active_ssid || root.network.connectivity === "full" ? T.StyleManager.success : T.StyleManager.warning; font.pixelSize: 25; font.bold: true; wrapMode: Text.WordWrap }
                        Text { Layout.fillWidth: true; text: root.network.ip_address ? "Adresse IP  " + root.network.ip_address : "Aucune adresse IP"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                        Text { Layout.fillWidth: true; text: root.network.connectivity === "full" ? "Internet accessible" : (root.network.active_ssid ? "Wi-Fi connecté · Internet non confirmé" : "Aucune connexion Wi-Fi"); color: root.network.connectivity === "full" ? T.StyleManager.success : T.StyleManager.textSecondary; font.pixelSize: 15; wrapMode: Text.WordWrap }
                        Text { Layout.fillWidth: true; visible: root.maintenance.overlay_current === true; text: "Protection SD active : les changements Wi-Fi seront perdus au redémarrage. Désactivez-la avant de modifier durablement les réseaux."; color: T.StyleManager.warning; font.pixelSize: 13; wrapMode: Text.WordWrap }
                        Text { Layout.fillWidth: true; visible: !!root.network.error; text: root.network.error || ""; color: T.StyleManager.danger; font.pixelSize: 15; wrapMode: Text.WordWrap }
                        RowLayout { Layout.fillWidth: true
                            Text { Layout.fillWidth: true; text: "Radio Wi-Fi"; color: T.StyleManager.text; font.pixelSize: 18 }
                            Toggle { checked: root.network.wifi_enabled === true; enabled: root.network.available !== false && !root.network.busy; onToggled: value => root.actionRequested("wifi_radio:" + (value ? "on" : "off")) }
                        }
                        Item { Layout.fillHeight: true }
                        Button { Layout.fillWidth: true; text: root.network.busy ? "OPÉRATION EN COURS" : "ACTUALISER"; primary: true; enabled: !root.network.busy; onClicked: root.actionRequested("wifi_refresh") }
                        Button { Layout.fillWidth: true; text: "DÉCONNECTER"; subtext: "Reconnexion au prochain choix ou redémarrage"; enabled: !!root.network.active_ssid && !root.network.busy; onClicked: root.actionRequested("wifi_disconnect") }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Gestion Wi-Fi"
                    ColumnLayout { anchors.fill: parent; spacing: 10
                        RowLayout { Layout.fillWidth: true; Layout.minimumHeight: 54; Layout.preferredHeight: 54; Layout.maximumHeight: 54; spacing: 10
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "À PORTÉE"; primary: root.networkListMode === "available"; onClicked: root.networkListMode = "available" }
                            Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "MÉMORISÉS"; primary: root.networkListMode === "saved"; onClicked: root.networkListMode = "saved" }
                        }
                        ListView {
                            id: wifiList
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                            model: root.networkListMode === "available" ? (root.network.visible_networks || []) : (root.network.saved_networks || [])
                            delegate: Rectangle {
                                required property var modelData
                                width: ListView.view.width; height: root.networkListMode === "available" ? 78 : 108
                                radius: T.StyleManager.radiusSmall; color: T.StyleManager.surfaceRaised
                                border.width: 1; border.color: modelData.active ? T.StyleManager.accent : T.StyleManager.outline
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 9; spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 2
                                        Text { Layout.fillWidth: true; text: modelData.ssid || modelData.name; color: T.StyleManager.text; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight }
                                        Text { Layout.fillWidth: true; text: modelData.active ? "Connecté · " + modelData.signal + "%" : (modelData.available === false ? "Hors de portée" : modelData.signal + "%" + (modelData.secured ? " · Sécurisé" : " · Ouvert")); color: T.StyleManager.textSecondary; font.pixelSize: 13; elide: Text.ElideRight }
                                        Text { Layout.fillWidth: true; visible: root.networkListMode === "saved"; text: (modelData.autoconnect ? "Auto" : "Manuel") + (modelData.priority > 0 ? " · Préféré au démarrage" : ""); color: modelData.priority > 0 ? T.StyleManager.success : T.StyleManager.textSecondary; font.pixelSize: 12 }
                                    }
                                    Button {
                                        Layout.preferredWidth: 150; Layout.fillHeight: true
                                        visible: root.networkListMode === "available"
                                        text: modelData.active ? "CONNECTÉ" : (modelData.supported === false ? "ENTREPRISE" : (modelData.saved ? "CONNECTER" : "AJOUTER"))
                                        primary: modelData.active; enabled: !modelData.active && modelData.supported !== false && !root.network.busy
                                        onClicked: modelData.saved ? root.actionRequested("wifi_connect:" + modelData.uuid) : root.openNetwork(modelData.ssid, modelData.secured)
                                    }
                                    ColumnLayout {
                                        visible: root.networkListMode === "saved"; spacing: 4
                                        RowLayout {
                                            Button { Layout.preferredWidth: 122; Layout.preferredHeight: 42; text: modelData.active ? "CONNECTÉ" : "CONNECTER"; primary: modelData.active === true; enabled: modelData.available === true && !modelData.active && !root.network.busy; onClicked: root.actionRequested("wifi_connect:" + modelData.uuid) }
                                            Button { Layout.preferredWidth: 112; Layout.preferredHeight: 42; text: "PRÉFÉRER"; primary: modelData.priority > 0; enabled: !root.network.busy; onClicked: root.actionRequested("wifi_prefer:" + modelData.uuid) }
                                        }
                                        RowLayout {
                                            Button { Layout.preferredWidth: 122; Layout.preferredHeight: 42; text: modelData.autoconnect ? "AUTO OUI" : "AUTO NON"; primary: modelData.autoconnect === true; enabled: !root.network.busy; onClicked: root.actionRequested("wifi_autoconnect:" + modelData.uuid + ":" + (modelData.autoconnect ? "off" : "on")) }
                                            Button { Layout.preferredWidth: 112; Layout.preferredHeight: 42; text: "OUBLIER"; destructive: true; enabled: !root.network.busy; onClicked: root.confirmForget(modelData.uuid, modelData.ssid) }
                                        }
                                    }
                                }
                            }
                            Text { anchors.centerIn: parent; visible: wifiList.count === 0; text: root.networkListMode === "available" ? "Aucun réseau détecté" : "Aucun réseau mémorisé"; color: T.StyleManager.textSecondary; font.pixelSize: 20 }
                        }
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

    Item {
        anchors.fill: parent; z: 1000; visible: root.networkDialogMode !== ""
        Rectangle { anchors.fill: parent; color: "#B0000000" }
        MouseArea { anchors.fill: parent }
        Rectangle {
            anchors.centerIn: parent; width: root.networkDialogMode === "password" ? 1040 : 720; height: root.networkDialogMode === "password" ? 660 : 280
            radius: T.StyleManager.radiusLarge; color: T.StyleManager.surfaceRaised
            border.width: 2; border.color: T.StyleManager.accent
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 28; spacing: 16
                Text { Layout.fillWidth: true; text: root.networkDialogMode === "password" ? "Connexion à " + root.selectedSsid : "Oublier " + root.selectedSsid + " ?"; color: T.StyleManager.text; font.pixelSize: 25; font.bold: true; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                Text { Layout.fillWidth: true; visible: root.networkDialogMode === "forget"; text: "Le mot de passe enregistré sera supprimé du Raspberry Pi."; color: T.StyleManager.textSecondary; font.pixelSize: 17; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                QC.TextField {
                    id: wifiPassword
                    objectName: "wifiPasswordField"
                    Layout.fillWidth: true; Layout.preferredHeight: 64
                    visible: root.networkDialogMode === "password"; placeholderText: "Mot de passe Wi-Fi"
                    echoMode: root.showWifiPassword ? TextInput.Normal : TextInput.Password; passwordMaskDelay: 800
                    inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                    color: T.StyleManager.text; font.pixelSize: 20; selectByMouse: true
                    background: Rectangle { radius: T.StyleManager.radiusSmall; color: T.StyleManager.surface; border.width: 1; border.color: wifiPassword.activeFocus ? T.StyleManager.accent : T.StyleManager.outline }
                    onVisibleChanged: if (visible) { text = ""; forceActiveFocus() }
                }
                GridLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 250; columns: 10
                    rowSpacing: 6; columnSpacing: 6; visible: root.networkDialogMode === "password"
                    Repeater {
                        model: root.wifiKeys
                        Button {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 44
                            text: root.keyboardShift ? String(modelData).toUpperCase() : String(modelData)
                            onClicked: {
                                wifiPassword.insert(wifiPassword.cursorPosition, text)
                                wifiPassword.forceActiveFocus()
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 48
                    visible: root.networkDialogMode === "password"; spacing: 8
                    Button { Layout.preferredWidth: 170; Layout.fillHeight: true; text: root.keyboardShift ? "MINUSCULES" : "MAJUSCULES"; primary: root.keyboardShift; onClicked: root.keyboardShift = !root.keyboardShift }
                    Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "ESPACE"; onClicked: wifiPassword.insert(wifiPassword.cursorPosition, " ") }
                    Button { Layout.preferredWidth: 190; Layout.fillHeight: true; text: root.showWifiPassword ? "MASQUER" : "AFFICHER"; onClicked: root.showWifiPassword = !root.showWifiPassword }
                    Button { Layout.preferredWidth: 190; Layout.fillHeight: true; text: "EFFACER"; onClicked: if (wifiPassword.cursorPosition > 0) wifiPassword.remove(wifiPassword.cursorPosition - 1, wifiPassword.cursorPosition) }
                }
                Item { Layout.fillHeight: true }
                RowLayout { Layout.fillWidth: true; spacing: 12
                    Button { Layout.fillWidth: true; text: "ANNULER"; onClicked: { root.networkDialogMode = ""; wifiPassword.text = ""; root.showWifiPassword = false; root.keyboardShift = false } }
                    Button {
                        Layout.fillWidth: true; primary: root.networkDialogMode === "password"; destructive: root.networkDialogMode === "forget"
                        text: root.networkDialogMode === "password" ? "CONNECTER" : "OUBLIER"
                        enabled: root.networkDialogMode === "forget" || wifiPassword.text.length >= 8
                        onClicked: {
                            if (root.networkDialogMode === "password") root.actionRequested("wifi_add:" + encodeURIComponent(root.selectedSsid) + ":" + encodeURIComponent(wifiPassword.text))
                            else root.actionRequested("wifi_forget:" + root.selectedUuid)
                            root.networkDialogMode = ""; wifiPassword.text = ""; root.showWifiPassword = false; root.keyboardShift = false
                        }
                    }
                }
            }
        }
    }
}
