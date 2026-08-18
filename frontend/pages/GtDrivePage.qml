import QtQuick
import QtQuick.Layouts
import "../components"
import "../style" as T
import "../state" as S

Item {
    id: root

    GridLayout {
        anchors.fill: parent
        anchors.margins: 16
        columns: 3
        rows: 2
        columnSpacing: 14
        rowSpacing: 14

        GtCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.columnSpan: 2
            title: "CliOS GT · conduite"
            highlighted: S.UiState.tripActive

            RowLayout {
                anchors.fill: parent
                spacing: 28
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: S.UiState.profileName()
                        color: T.StyleManager.text
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: S.UiState.tripActive ? "Trajet en cours · enregistrement actif" :
                              (S.UiState.sessionState === "PAUSED" ? "Trajet en pause" : "Prêt à prendre la route")
                        color: S.UiState.tripActive ? T.StyleManager.success : T.StyleManager.textSecondary
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 19
                    }
                }
                GtMetric {
                    Layout.preferredWidth: 230
                    label: "Odomètre"
                    value: S.UiState.fixed(S.UiState.odometer, 0, "0")
                    unit: "km"
                    alignment: Text.AlignRight
                }
            }
        }

        GtCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Consommation"
            ColumnLayout {
                anchors.fill: parent
                spacing: 12
                GtMetric {
                    Layout.fillWidth: true
                    label: "Instantanée"
                    value: S.UiState.fixed(S.UiState.trip.inst_cons, 1, "0,0")
                    unit: "L/100"
                }
                GtMetric {
                    Layout.fillWidth: true
                    label: "Moyenne trajet"
                    value: S.UiState.fixed(S.UiState.trip.avg_cons_session, 1, "0,0")
                    unit: "L/100"
                    valueSize: 28
                }
            }
        }

        GtCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Ordinateur de bord"
            RowLayout {
                anchors.fill: parent
                spacing: 28
                GtMetric { Layout.fillWidth: true; label: "Trip A"; value: S.UiState.fixed(S.UiState.trip.trip_a, 1, "0,0"); unit: "km" }
                GtMetric { Layout.fillWidth: true; label: "Trip B"; value: S.UiState.fixed(S.UiState.trip.trip_b, 1, "0,0"); unit: "km" }
                GtMetric { Layout.fillWidth: true; label: "Moy. B"; value: S.UiState.fixed(S.UiState.trip.avg_cons_b, 1, "0,0"); unit: "L/100" }
            }
        }

        GtCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Maintenance"
            GtMetric {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width * 0.44
                label: "Révision"
                value: S.UiState.fixed(S.UiState.trip.km_before_service, 0, "—")
                unit: "km"
                valueColor: S.UiState.trip.service_warning ? T.StyleManager.warning : T.StyleManager.text
            }
            GtProgress {
                anchors.left: parent.horizontalCenter
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                height: 12
                value: S.UiState.number(S.UiState.trip.km_before_service, 0)
                to: 20000
                fillColor: S.UiState.trip.service_warning ? T.StyleManager.warning : T.StyleManager.success
            }
        }

        GtCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "État véhicule"
            highlighted: S.UiState.attentionVehicle
            RowLayout {
                anchors.fill: parent
                spacing: 12
                Text {
                    Layout.fillWidth: true
                    text: S.UiState.attentionVehicle ? "ATTENTION REQUISE" : "VÉHICULE PRÊT"
                    color: S.UiState.attentionVehicle ? T.StyleManager.warning : T.StyleManager.success
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: S.UiState.attentionVehicle ? 20 : 22
                    font.weight: Font.Bold
                    wrapMode: Text.WordWrap
                }
                Column {
                    Layout.preferredWidth: 155
                    spacing: 5
                    Text { text: S.UiState.vehicle.driver_unbelted ? "Ceinture conducteur" : "Ceinture bouclée"; color: T.StyleManager.textSecondary; font.pixelSize: 17 }
                    Text { text: S.UiState.doorOpen ? "Ouvrant ouvert" : "Ouvrants contrôlés"; color: T.StyleManager.textSecondary; font.pixelSize: 17 }
                }
            }
        }
    }
}
