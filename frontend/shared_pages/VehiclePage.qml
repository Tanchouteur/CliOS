import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    property string initialRoute: "vehicle"
    property int tab: initialRoute === "diagnostic" ? 1 : (initialRoute === "transmission" ? 2 : 0)
    readonly property var tabs: ["ENTRETIEN", "DIAGNOSTIC OBD", "TRANSMISSION"]
    signal actionRequested(string action)
    signal backRequested()
    onInitialRouteChanged: tab = initialRoute === "diagnostic" ? 1 : (initialRoute === "transmission" ? 2 : 0)
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Véhicule"; subtitle: "Entretien, diagnostic et transmission"; showBack: false }
        RowLayout { Layout.fillWidth: true; Layout.minimumHeight: 64; Layout.preferredHeight: 64; Layout.maximumHeight: 64; spacing: 10
            Repeater { model: root.tabs; Button { Layout.fillWidth: true; Layout.minimumHeight: 56; Layout.maximumHeight: 64; text: modelData; primary: root.tab === index; onClicked: root.tab = index } }
        }
        Item { Layout.fillWidth: true; Layout.fillHeight: true
            RowLayout { anchors.fill: parent; visible: root.tab === 0; spacing: 14
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Prochaine révision"; highlighted: S.UiState.serviceWarning
                    ColumnLayout { anchors.fill: parent; spacing: 16
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: "Distance restante"; value: S.UiState.fixed(S.UiState.kmBeforeService, 0, "—"); unit: "km"; alignment: Text.AlignHCenter; valueSize: 48 }
                        Text { Layout.fillWidth: true; text: "Intervalle configuré : " + S.UiState.fixed(S.UiState.revisionIntervalKm, 0, "—") + " km"; color: T.StyleManager.textSecondary; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter }
                        Button { Layout.fillWidth: true; Layout.preferredHeight: 72; text: "VALIDER LA RÉVISION"; primary: true; onClicked: root.actionRequested("reset_maintenance") }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "État mécanique"
                    GridLayout { anchors.fill: parent; columns: 2; rowSpacing: 12; columnSpacing: 12
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: "Température moteur"; value: S.UiState.fixed(S.UiState.engineTemp, 0, "—"); unit: "°C"; alignment: Text.AlignHCenter }
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: "Kilométrage"; value: S.UiState.fixed(S.UiState.odometer, 0, "—"); unit: "km"; alignment: Text.AlignHCenter }
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: "Carburant"; value: S.UiState.fixed(S.UiState.fuelLevel, 0, "—"); unit: "%"; alignment: Text.AlignHCenter }
                        Metric { Layout.fillWidth: true; Layout.fillHeight: true; label: "Alertes"; value: S.UiState.engineWarning || S.UiState.serviceWarning ? "À CONTRÔLER" : "OK"; alignment: Text.AlignHCenter; valueSize: 25 }
                    }
                }
            }
            RowLayout { anchors.fill: parent; visible: root.tab === 1; spacing: 14
                Card { Layout.preferredWidth: 390; Layout.fillHeight: true; title: "Calculateur moteur"; highlighted: S.UiState.diagnosticCodes.length > 0
                    ColumnLayout { anchors.fill: parent; spacing: 14
                        Item { Layout.fillHeight: true }
                        Text { Layout.fillWidth: true; text: S.UiState.isScanning ? "ANALYSE EN COURS" : (S.UiState.hasScanned ? (S.UiState.diagnosticCodes.length ? "DÉFAUTS DÉTECTÉS" : "AUCUN DÉFAUT") : "PRÊT"); color: S.UiState.diagnosticCodes.length ? T.StyleManager.danger : T.StyleManager.success; font.pixelSize: 28; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: "Lecture des codes défaut OBD-II mémorisés"; color: T.StyleManager.textSecondary; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                        Item { Layout.fillHeight: true }
                        Button { Layout.fillWidth: true; Layout.preferredHeight: 72; text: "LANCER LE DIAGNOSTIC"; primary: true; enabled: !S.UiState.isScanning; onClicked: root.actionRequested("diagnostic_scan") }
                    }
                }
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Codes défaut"
                    ListView { anchors.fill: parent; clip: true; spacing: 10; model: S.UiState.diagnosticCodes
                        delegate: Rectangle { width: ListView.view.width; height: 72; radius: T.StyleManager.radiusSmall; color: T.StyleManager.surfaceRaised; border.width: 1; border.color: T.StyleManager.danger
                            Text { anchors.left: parent.left; anchors.leftMargin: 20; anchors.verticalCenter: parent.verticalCenter; text: String(modelData); color: T.StyleManager.danger; font.pixelSize: 25; font.bold: true }
                        }
                        Text { anchors.centerIn: parent; visible: S.UiState.diagnosticCodes.length === 0; text: S.UiState.hasScanned ? "Aucun code défaut" : "Lancez une analyse pour afficher le rapport"; color: T.StyleManager.textSecondary; font.pixelSize: 20 }
                    }
                }
            }
            Card { anchors.fill: parent; visible: root.tab === 2; title: "Transmission · " + (S.UiState.isAutomaticGearbox ? "Automatique" : "Manuelle")
                RowLayout { anchors.fill: parent; spacing: 12
                    Repeater { model: S.UiState.isAutomaticGearbox ? ["P", "R", "N", "D"] : ["1", "2", "3", "4", "5", "6"]
                        Card { Layout.fillWidth: true; Layout.fillHeight: true; highlighted: S.UiState.gear === modelData
                            Metric { anchors.centerIn: parent; width: parent.width; label: "Rapport " + modelData; value: S.UiState.gearRatios[modelData] !== undefined ? S.UiState.fixed(S.UiState.gearRatios[modelData], 2, "—") : (S.UiState.gear === modelData ? "ENGAGÉ" : "—"); alignment: Text.AlignHCenter; valueSize: 23 }
                        }
                    }
                }
            }
        }
    }
}
