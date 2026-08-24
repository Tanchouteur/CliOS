import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal actionRequested(string action)
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 14
        PageHeader { Layout.fillWidth: true; title: "Conduite"; subtitle: "Trajet en cours et état essentiel du véhicule"; showBack: false }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 210; spacing: 14
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Trip A"
                Metric { anchors.centerIn: parent; width: parent.width; label: "Distance"; value: S.UiState.fixed(S.UiState.tripA, 1, "0,0"); unit: "km"; alignment: Text.AlignHCenter; valueSize: 40 }
            }
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Trip B"
                Metric { anchors.centerIn: parent; width: parent.width; label: "Moyenne " + S.UiState.fixed(S.UiState.avgConsB, 1, "—") + " l/100"; value: S.UiState.fixed(S.UiState.tripB, 1, "0,0"); unit: "km"; alignment: Text.AlignHCenter; valueSize: 40 }
            }
            Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Session"; highlighted: S.UiState.tripActive
                Column { anchors.centerIn: parent; spacing: 8
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.sessionState; color: S.UiState.tripActive ? T.StyleManager.success : T.StyleManager.textSecondary; font.pixelSize: 30; font.bold: true }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0") + " km · " + S.UiState.fixed(S.UiState.avgConsSession, 1, "—") + " l/100"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 132; title: "Commandes du trajet"
            RowLayout { anchors.fill: parent; spacing: 12
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "REMETTRE A À ZÉRO"; onClicked: root.actionRequested("reset_a") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "REMETTRE B À ZÉRO"; onClicked: root.actionRequested("reset_b") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; primary: true; text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE" : "METTRE EN PAUSE"; enabled: S.UiState.tripActive || S.UiState.sessionState === "PAUSED"; onClicked: root.actionRequested(S.UiState.sessionState === "PAUSED" ? "resume_trip" : "pause_trip") }
                Button { Layout.fillWidth: true; Layout.fillHeight: true; destructive: true; text: "TERMINER LE TRAJET"; enabled: S.UiState.tripActive || S.UiState.sessionState === "PAUSED"; onClicked: root.actionRequested("end_trip") }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "État synthétique du véhicule"
            RowLayout { anchors.fill: parent; spacing: 12
                Metric { Layout.fillWidth: true; label: "Carburant"; value: S.UiState.fixed(S.UiState.fuelLevel, 0, "—"); unit: "%"; alignment: Text.AlignHCenter }
                Metric { Layout.fillWidth: true; label: "Autonomie"; value: S.UiState.fixed(S.UiState.autonomy, 0, "—"); unit: "km"; alignment: Text.AlignHCenter }
                Metric { Layout.fillWidth: true; label: "Moteur"; value: S.UiState.fixed(S.UiState.engineTemp, 0, "—"); unit: "°C"; alignment: Text.AlignHCenter }
                Metric { Layout.fillWidth: true; label: "Révision dans"; value: S.UiState.fixed(S.UiState.kmBeforeService, 0, "—"); unit: "km"; alignment: Text.AlignHCenter }
                ColumnLayout { Layout.fillWidth: true; spacing: 8
                    Text { Layout.alignment: Qt.AlignHCenter; text: S.UiState.attentionVehicle || S.UiState.engineWarning ? "ATTENTION" : "VÉHICULE OK"; color: S.UiState.attentionVehicle || S.UiState.engineWarning ? T.StyleManager.warning : T.StyleManager.success; font.pixelSize: 23; font.bold: true }
                    Text { Layout.fillWidth: true; text: S.UiState.doorOpen ? "Ouvrant détecté" : (S.UiState.driverUnbelted ? "Ceinture conducteur" : "Aucune alerte prioritaire"); color: T.StyleManager.textSecondary; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter }
                }
            }
        }
    }
}
