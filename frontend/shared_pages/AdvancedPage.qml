import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    property string initialRoute: "advanced"
    property int tab: initialRoute === "services" ? 1 : (["developer","can"].indexOf(initialRoute) >= 0 ? 2 : (initialRoute === "logs" ? 3 : 0))
    property var profiles: []
    property string activeProfile: ""
    property string logsText: ""
    property string exportPath: ""
    readonly property var tabs: ["PROFILS VÉHICULE", "SERVICES", "DONNÉES CAN", "JOURNAUX"]
    signal actionRequested(string action)
    onInitialRouteChanged: tab = initialRoute === "services" ? 1 : (["developer","can"].indexOf(initialRoute) >= 0 ? 2 : (initialRoute === "logs" ? 3 : 0))
    function refreshProfiles() { profiles = bridge.getAvailableProfiles(); activeProfile = bridge.getActiveProfile() }
    Component.onCompleted: refreshProfiles()
    Timer { interval: 1500; running: root.visible && root.tab === 3; repeat: true; triggeredOnStart: true
        onTriggered: { try { const rows=JSON.parse(bridge.getRecentLogs(120) || "[]"); root.logsText=rows.map(e => "["+e.ts+"] ["+e.level+"] "+e.logger+" — "+e.message).join("\n") } catch(error) { root.logsText="Journaux indisponibles" } }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Avancé"; subtitle: S.UiState.recoveryMode ? "Mode de récupération · " + S.UiState.recoveryMessage : "Profils, services et outils de diagnostic"; showBack: false }
        RowLayout { Layout.fillWidth: true; Layout.minimumHeight: 64; Layout.preferredHeight: 64; Layout.maximumHeight: 64; spacing: 10
            Repeater { model: root.tabs; Button { Layout.fillWidth: true; Layout.minimumHeight: 56; Layout.maximumHeight: 64; text: modelData; primary: root.tab === index; onClicked: root.tab=index } }
        }
        Item { Layout.fillWidth: true; Layout.fillHeight: true
            RowLayout { anchors.fill: parent; visible: root.tab === 0; spacing: 14
                Card { Layout.preferredWidth: 520; Layout.fillHeight: true; title: "Profils disponibles"
                    ListView { anchors.fill: parent; clip: true; spacing: 10; model: root.profiles
                        delegate: Button { width: ListView.view.width; height: 74
                            property string profileId: typeof modelData === "object" ? String(modelData.id || modelData.profile_id || "") : String(modelData)
                            text: typeof modelData === "object" ? String(modelData.name || profileId) : profileId
                            subtext: profileId === root.activeProfile ? "Profil actif" : "Toucher pour activer"
                            primary: profileId === root.activeProfile; enabled: profileId !== root.activeProfile
                            onClicked: root.actionRequested("activate_profile:" + profileId)
                        }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Activation sécurisée"; highlighted: S.UiState.recoveryMode
                    ColumnLayout { anchors.fill: parent; spacing: 16
                        Text { Layout.fillWidth: true; text: S.UiState.recoveryMode ? "CONFIGURATION À RÉCUPÉRER" : "PROFIL ACTIF"; color: S.UiState.recoveryMode ? T.StyleManager.warning : T.StyleManager.success; font.pixelSize: 19; font.bold: true }
                        Text { Layout.fillWidth: true; text: root.activeProfile || "Aucun profil valide"; color: T.StyleManager.text; font.pixelSize: 38; font.bold: true; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: "Le changement de profil modifie la configuration véhicule et les données CAN. Une confirmation est demandée, puis CliOS redémarre automatiquement."; color: T.StyleManager.textSecondary; font.pixelSize: 17; wrapMode: Text.WordWrap }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
            Loader {
                anchors.fill: parent
                visible: root.tab === 1
                active: root.tab === 1
                source: "ServicesPage.qml"
                onLoaded: item.embedded = true
            }
            Card { anchors.fill: parent; visible: root.tab === 2; title: "Données CAN normalisées"
                GridView { anchors.fill: parent; clip: true; cellWidth: width/3; cellHeight: 72; model: S.UiState.debugSignals
                    delegate: Rectangle { width: GridView.view.cellWidth-10; height: 62; radius: T.StyleManager.radiusSmall; color: index%2 ? T.StyleManager.surfaceRaised : T.StyleManager.surfaceSoft
                        RowLayout { anchors.fill: parent; anchors.margins: 10
                            ColumnLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.domain+" · "+modelData.key; color:T.StyleManager.text; font.pixelSize:14; elide:Text.ElideRight } Text { text:modelData.source+" · "+modelData.quality; color:T.StyleManager.textSecondary; font.pixelSize:11 } }
                            Text { text:String(modelData.value)+(modelData.unit ? " "+modelData.unit : ""); color:T.StyleManager.accent; font.family:T.StyleManager.fontMono; font.pixelSize:14 }
                        }
                    }
                }
            }
            ColumnLayout { anchors.fill: parent; visible: root.tab === 3; spacing: 12
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Journal système"
                    Flickable { anchors.fill: parent; clip: true; contentWidth: width; contentHeight: logText.implicitHeight
                        Text { id: logText; width: parent.width; text: root.logsText; color: T.StyleManager.textSecondary; font.family: T.StyleManager.fontMono; font.pixelSize: 13; wrapMode: Text.WrapAnywhere }
                    }
                }
                Button { Layout.fillWidth: true; Layout.preferredHeight: 72; text: "EXPORTER LE DIAGNOSTIC"; subtext: root.exportPath || "Journaux, configuration et état système"; primary: true; onClicked: root.exportPath=bridge.exportDiagnosticBundle() }
            }
        }
    }
}
