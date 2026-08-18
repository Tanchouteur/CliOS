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
    property var profiles: []
    property var canFiles: []
    property var configFiles: []
    property string activeProfile: ""
    property string pendingProfile: ""

    function refresh() {
        profiles = bridge.getAvailableProfiles()
        canFiles = bridge.getAvailableCanFiles()
        configFiles = bridge.getAvailableConfigFiles()
        activeProfile = bridge.getActiveProfile()
        if (!pendingProfile) pendingProfile = activeProfile
    }
    Component.onCompleted: refresh()

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        GtPageHeader { Layout.fillWidth: true; title: "Véhicule"; subtitle: "Profils, entretien et boîte de vitesses"; onBackClicked: root.backRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            GtCard {
                Layout.preferredWidth: 380; Layout.fillHeight: true; title: "Profils disponibles"
                ListView {
                    anchors.fill: parent; clip: true; spacing: 10; model: root.profiles
                    delegate: GtButton {
                        width: ListView.view.width; height: 72
                        text: String(modelData)
                        subtext: String(modelData) === root.activeProfile ? "Profil chargé" : (String(modelData) === root.pendingProfile ? "Redémarrage requis" : "Disponible")
                        primary: String(modelData) === root.pendingProfile
                        onClicked: { if (bridge.setActiveProfile(String(modelData))) root.pendingProfile = String(modelData) }
                    }
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Ajouter un profil"
                GridLayout {
                    anchors.fill: parent; columns: 2; rowSpacing: 12; columnSpacing: 14
                    TextField { id: profileId; Layout.fillWidth: true; Layout.preferredHeight: 58; placeholderText: "Identifiant technique"; color: T.StyleManager.text; font.pixelSize: 18; background: Rectangle { color: T.StyleManager.surfaceRaised; radius: T.StyleManager.radiusSmall; border.color: T.StyleManager.outline } }
                    TextField { id: profileName; Layout.fillWidth: true; Layout.preferredHeight: 58; placeholderText: "Nom d’affichage"; color: T.StyleManager.text; font.pixelSize: 18; background: Rectangle { color: T.StyleManager.surfaceRaised; radius: T.StyleManager.radiusSmall; border.color: T.StyleManager.outline } }
                    ComboBox { id: canCombo; Layout.fillWidth: true; Layout.preferredHeight: 58; model: root.canFiles; font.pixelSize: 17 }
                    ComboBox { id: configCombo; Layout.fillWidth: true; Layout.preferredHeight: 58; model: root.configFiles; font.pixelSize: 17 }
                    GtButton {
                        Layout.columnSpan: 2; Layout.fillWidth: true; text: "CRÉER LE PROFIL"
                        enabled: profileId.text.length > 0 && profileName.text.length > 0 && canCombo.currentText.length > 0 && configCombo.currentText.length > 0
                        onClicked: {
                            if (bridge.createNewProfile(profileId.text, profileName.text, canCombo.currentText, configCombo.currentText, "save_" + profileId.text + ".json")) {
                                profileId.clear(); profileName.clear(); root.refresh()
                            }
                        }
                    }
                    GtButton { Layout.fillWidth: true; text: "ÉTALONNER LES RAPPORTS"; onClicked: bridge.startGearCalibration() }
                    GtButton { Layout.fillWidth: true; text: "TERMINER L’ÉTALONNAGE"; onClicked: bridge.stopGearCalibration() }
                    GtButton { Layout.fillWidth: true; text: "RÉVISION EFFECTUÉE"; onClicked: root.actionRequested("reset_maintenance") }
                    GtButton { Layout.fillWidth: true; text: "REDÉMARRER SUR LE PROFIL"; destructive: true; enabled: root.pendingProfile !== root.activeProfile; onClicked: root.actionRequested("restart") }
                }
            }
        }
    }
}
