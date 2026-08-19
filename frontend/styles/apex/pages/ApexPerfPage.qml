import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "../components"

// Page performance — 3 grandes cartes avec jauges
Item {
    id: root
    anchors.fill: parent

    signal actionRequested(string action)
    signal navigateRequested(string target)

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // ── Puissance ──────────────────────────────────────────────────
        ApexCard3D {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Puissance"

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                ApexGaugeArc {
                    Layout.alignment: Qt.AlignHCenter
                    width: 180; height: 180
                    label: "kW"
                    unit: "kW"
                    value: S.UiState.power
                    from: 0; to: 200
                    baseColor: T.StyleManager.accent
                }

                // Chiffre géant
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: S.UiState.fixed(S.UiState.power, 1, "—")
                    color: T.StyleManager.accent
                    font.pixelSize: 52
                    font.weight: Font.Black
                    font.letterSpacing: -1
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Couple"
                        value: S.UiState.fixed(S.UiState.torque, 0, "—")
                        unit: "N·m"
                        valueSize: 22
                        alignment: Text.AlignHCenter
                    }
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Papillon"
                        value: S.UiState.fixed(S.UiState.throttle, 0, "—")
                        unit: "%"
                        valueSize: 22
                        alignment: Text.AlignHCenter
                    }
                }
            }
        }

        // ── Régime ─────────────────────────────────────────────────────
        ApexCard3D {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Régime moteur"
            highlighted: S.UiState.redline
            glowColor: S.UiState.redline ? "#FF1744" : T.StyleManager.accent

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                ApexGaugeArc {
                    Layout.alignment: Qt.AlignHCenter
                    width: 180; height: 180
                    label: "RPM"
                    unit: ""
                    value: S.UiState.rpm
                    from: 0
                    to: S.UiState.maxRpm > 0 ? S.UiState.maxRpm : 7000
                    warningAt: S.UiState.maxRpm > 0 ? S.UiState.redlineRpm / S.UiState.maxRpm : 0.85
                    baseColor: S.UiState.redline ? "#FF1744" : T.StyleManager.accent
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Math.round(S.UiState.rpm)
                    color: S.UiState.redline ? "#FF1744" : "#FFFFFF"
                    font.pixelSize: 48
                    font.weight: Font.Black
                    font.letterSpacing: -1
                    Behavior on color { ColorAnimation { duration: 200 } }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "tr/min"
                    color: Qt.rgba(1,1,1,0.3)
                    font.pixelSize: 14
                    font.letterSpacing: 2
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Zone rouge"
                        value: Math.round(S.UiState.redlineRpm)
                        unit: "tr/min"
                        valueSize: 18
                        alignment: Text.AlignHCenter
                        valueColor: "#FF4444"
                    }
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Rapport"
                        value: S.UiState.gear
                        valueSize: 32
                        alignment: Text.AlignHCenter
                        valueColor: S.UiState.redline ? "#FF4444" : T.StyleManager.accent
                    }
                }
            }
        }

        // ── Efficience ─────────────────────────────────────────────────
        ApexCard3D {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Efficience"

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                ApexGaugeArc {
                    Layout.alignment: Qt.AlignHCenter
                    width: 180; height: 180
                    label: "L/100"
                    unit: "L/100"
                    value: Math.min(S.UiState.instantCons, 25)
                    from: 0
                    to: S.UiState.instantConsMax > 0 ? S.UiState.instantConsMax : 25
                    warningAt: 0.60
                    baseColor: S.UiState.instantCons > 15 ? "#FF6B00" : "#00E676"
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: S.UiState.fixed(S.UiState.instantCons, 1, "—")
                    color: S.UiState.instantCons > 15 ? "#FFB300" : "#00E676"
                    font.pixelSize: 52
                    font.weight: Font.Black
                    font.letterSpacing: -1
                    Behavior on color { ColorAnimation { duration: 300 } }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Moy. B"
                        value: S.UiState.fixed(S.UiState.avgConsB, 1, "—")
                        unit: "L/100"
                        valueSize: 22
                        alignment: Text.AlignHCenter
                    }
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Turbo"
                        value: S.UiState.fixed(S.UiState.boostPsi, 1, "—")
                        unit: "psi"
                        valueSize: 22
                        alignment: Text.AlignHCenter
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Qt.rgba(1,1,1,0.07)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Distance"
                        value: S.UiState.fixed(S.UiState.tripDistance, 1, "0")
                        unit: "km"
                        valueSize: 20
                        alignment: Text.AlignHCenter
                    }
                    ApexMetric {
                        Layout.fillWidth: true
                        label: "Régime Moy."
                        value: Math.round(S.UiState.avgRpm)
                        unit: "RPM"
                        valueSize: 20
                        alignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
