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
                        onClicked: { root.pendingProfile = String(modelData); bridge.switchProfile(String(modelData)) }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                GtCard {
                    Layout.fillWidth: true; Layout.preferredHeight: 180; title: "Entretien"
                    RowLayout {
                        anchors.fill: parent; spacing: 20
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Text { text: "Prochaine révision dans"; color: T.StyleManager.textSecondary; font.pixelSize: 15 }
                            Text { text: S.UiState.fixed(S.UiState.maintenanceRemainingKm, 0, "—") + " km"; color: S.UiState.maintenanceRemainingKm < 1500 ? T.StyleManager.warning : T.StyleManager.text; font.pixelSize: 36; font.bold: true }
                            Text { text: "Intervalle nominal: " + S.UiState.fixed(S.UiState.maintenanceIntervalKm, 0, "—") + " km"; color: T.StyleManager.textSecondary; font.pixelSize: 14 }
                        }
                        GtButton { width: 260; height: 68; text: "VALIDER LA RÉVISION"; primary: true; onClicked: root.actionRequested("reset_maintenance") }
                    }
                }
                GtCard {
                    Layout.fillWidth: true; Layout.fillHeight: true; title: "Rapports de boîte"
                    RowLayout {
                        anchors.fill: parent; spacing: 12
                        Repeater {
                            model: ["1", "2", "3", "4", "5", "6"]
                            delegate: GtCard {
                                Layout.fillWidth: true; Layout.fillHeight: true; highlighted: S.UiState.currentGear === modelData
                                GtMetric { anchors.centerIn: parent; width: parent.width; label: "Rapport " + modelData; value: (S.UiState.gearRatios && S.UiState.gearRatios[modelData] !== undefined) ? S.UiState.fixed(S.UiState.gearRatios[modelData], 2, "—") : "—"; alignment: Text.AlignHCenter; valueSize: 24 }
                            }
                        }
                    }
                }
            }
        }
    }
}
