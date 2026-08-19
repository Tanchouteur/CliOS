import QtQuick
import QtQuick.Layouts
import "../components"
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    signal actionRequested(string action)

    function adjustFuelPrice(delta) {
        const current = S.UiState.number(S.UiState.trip.fuel_price, 1.70)
        const next = Math.max(0.50, Math.min(3.50, Math.round((current + delta) * 100) / 100))
        bridge.updateFuelPrice(next)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            Layout.maximumHeight: 170
            spacing: 14
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Bilan du trajet"
                RowLayout {
                    anchors.fill: parent; spacing: 30
                    GtMetric { Layout.preferredWidth: 190; Layout.minimumWidth: 190; label: "Distance"; value: S.UiState.fixed(S.UiState.trip.distance_km, 1, "0,0"); unit: "km" }
                    GtMetric { Layout.preferredWidth: 220; Layout.minimumWidth: 220; label: "Carburant"; value: S.UiState.fixed(S.UiState.trip.session_fuel_l, 2, "0,00"); unit: "L" }
                    GtMetric { Layout.preferredWidth: 220; Layout.minimumWidth: 220; label: "Coût estimé"; value: S.UiState.fixed(S.UiState.trip.session_cost, 2, "0,00"); unit: "€" }
                    Item { Layout.fillWidth: true }
                }
            }
            GtCard {
                Layout.preferredWidth: 360; Layout.minimumWidth: 360; Layout.maximumWidth: 360
                Layout.fillHeight: true; title: "État · prix carburant"
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Text {
                        Layout.fillWidth: true
                        text: S.UiState.tripActive ? "ENREGISTREMENT ACTIF" : S.UiState.sessionState
                        color: S.UiState.tripActive ? T.StyleManager.danger : T.StyleManager.textSecondary
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        horizontalAlignment: Text.AlignHCenter
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        GtButton { Layout.preferredWidth: 68; Layout.preferredHeight: 54; text: "−"; onClicked: root.adjustFuelPrice(-0.01) }
                        Text {
                            Layout.fillWidth: true
                            text: S.UiState.fixed(S.UiState.trip.fuel_price, 2, "1,70") + " €/L"
                            color: T.StyleManager.text
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 25
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                        }
                        GtButton { Layout.preferredWidth: 68; Layout.preferredHeight: 54; text: "+"; onClicked: root.adjustFuelPrice(0.01) }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 340
            spacing: 14
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Éco-conduite"
                ColumnLayout {
                    anchors.fill: parent; spacing: 18
                    GtMetric { Layout.fillWidth: true; label: "Agressivité moyenne"; value: S.UiState.fixed(S.UiState.trip.aggressivity_pct, 0, "0"); unit: "%" }
                    GtMetric { Layout.fillWidth: true; label: "Décél. sans accélérateur"; value: S.UiState.fixed(S.UiState.decelerationWithoutThrottleKm, 1, "0,0"); unit: "km" }
                    GtProgress {
                        Layout.fillWidth: true; height: 12
                        value: S.UiState.decelerationWithoutThrottleKm
                        to: Math.max(1, S.UiState.number(S.UiState.trip.distance_km, 1))
                        fillColor: T.StyleManager.success
                    }
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Mécanique"
                ColumnLayout {
                    anchors.fill: parent; spacing: 18
                    GtMetric { Layout.fillWidth: true; label: "Régime moyen"; value: S.UiState.fixed(S.UiState.trip.avg_rpm, 0, "0"); unit: "tr/min" }
                    GtMetric { Layout.fillWidth: true; label: "Passage de rapport"; value: S.UiState.fixed(S.UiState.trip.shift_time_sec, 2, "0,00"); unit: "s" }
                }
            }
            GtCard {
                Layout.preferredWidth: 340; Layout.fillHeight: true; title: "Actions"
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    GtButton { Layout.fillWidth: true; text: "REMETTRE TRIP A À ZÉRO"; onClicked: root.actionRequested("reset_a") }
                    GtButton { Layout.fillWidth: true; text: "REMETTRE TRIP B À ZÉRO"; onClicked: root.actionRequested("reset_b") }
                    GtButton {
                        Layout.fillWidth: true
                        text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE LE TRAJET" : "TERMINER LE TRAJET"
                        destructive: S.UiState.sessionState !== "PAUSED"
                        enabled: S.UiState.sessionState === "PAUSED" || S.UiState.tripActive
                        onClicked: root.actionRequested(S.UiState.sessionState === "PAUSED" ? "resume_trip" : "end_trip")
                    }
                }
            }
        }
    }
}
