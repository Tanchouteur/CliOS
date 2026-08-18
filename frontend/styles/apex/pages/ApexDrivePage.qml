import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "../components"

// Page de conduite principale — Hypercar Concept Layout 1920×720
Item {
    id: root
    anchors.fill: parent

    signal actionRequested(string action)
    signal navigateRequested(string target)

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 16

        // ══════════════════════════════════════════════════════════════════════
        //  AILE GAUCHE (460 px) — Carburant, Régulateur, Ordinateur de bord
        // ══════════════════════════════════════════════════════════════════════
        ColumnLayout {
            Layout.preferredWidth: 460
            Layout.minimumWidth: 440
            Layout.maximumWidth: 480
            Layout.fillHeight: true
            spacing: 12

            // ── 1. Carburant liquide & Autonomie ──────────────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                title: "Niveau Carburant"
                highlighted: S.UiState.lowFuel
                glowColor: S.UiState.lowFuel ? "#FF1744" : T.StyleManager.accent

                ApexFuelWave {
                    anchors.fill: parent
                    anchors.margins: 2
                }
            }

            // ── 2. Régulateur / Limiteur de vitesse ───────────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                title: "Régulateur / Limiteur"
                highlighted: S.UiState.cruiseMode !== "OFF"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 16

                    Column {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: S.UiState.cruiseMode
                            color: S.UiState.cruiseMode !== "OFF" ? T.StyleManager.accent : Qt.rgba(1,1,1,0.40)
                            font.pixelSize: 26
                            font.weight: Font.Black
                            font.letterSpacing: 1.5
                            Behavior on color { ColorAnimation { duration: 200 } }
                        }
                        Text {
                            text: S.UiState.cruiseStatus
                            color: S.UiState.cruiseStatus === "ACTIF" ? "#00E676" : Qt.rgba(1,1,1,0.45)
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            font.letterSpacing: 2.0
                        }
                    }

                    Row {
                        visible: S.UiState.cruiseTarget > 0
                        spacing: 4
                        Layout.alignment: Qt.AlignVCenter

                        Text {
                            text: Math.round(S.UiState.cruiseTarget)
                            color: "#FFFFFF"
                            font.pixelSize: 46
                            font.weight: Font.Black
                            font.letterSpacing: -1.0
                        }
                        Text {
                            text: "KM/H"
                            color: Qt.rgba(1,1,1,0.45)
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            anchors.baseline: parent.children[0].baseline
                        }
                    }

                    Text {
                        visible: S.UiState.cruiseTarget <= 0
                        text: "—"
                        color: Qt.rgba(1,1,1,0.30)
                        font.pixelSize: 36
                        font.weight: Font.Bold
                    }
                }
            }

            // ── 3. Ordinateur de bord & Trajet ────────────────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Ordinateur de Bord"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Trip A"
                            value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.trip_a : 0, 1, "0,0")
                            unit: "km"
                            valueSize: 24
                        }

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Trip B"
                            value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.trip_b : 0, 1, "0,0")
                            unit: "km"
                            valueSize: 24
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Conso Moy. B"
                            value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.avg_cons_b : 0, 1, "0,0")
                            unit: "L/100"
                            valueSize: 24
                        }

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Odomètre"
                            value: S.UiState.fixed(S.UiState.odometer, 0, "0")
                            unit: "km"
                            valueSize: 20
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Bouton Tactile d'Action de Trajet
                    Rectangle {
                        Layout.fillWidth: true
                        height: 44
                        radius: 10
                        color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.14)
                        border.width: 1.5
                        border.color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.55)

                        Text {
                            anchors.centerIn: parent
                            text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE TRAJET" : "PAUSE TRAJET"
                            color: "#FFFFFF"
                            font.pixelSize: 13
                            font.weight: Font.Black
                            font.letterSpacing: 2.0
                        }

                        MouseArea {
                            anchors.fill: parent
                            onPressed:  parent.opacity = 0.70
                            onReleased: parent.opacity = 1.00
                            onClicked: {
                                if (S.UiState.sessionState === "PAUSED") {
                                    bridge.resumeTripSession()
                                } else {
                                    root.actionRequested("end_trip")
                                }
                            }
                        }
                    }
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════════
        //  CŒUR CENTRAL (Grand Compteur 3D Holographique)
        // ══════════════════════════════════════════════════════════════════════
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 500

            ApexSpeedometer {
                anchors.centerIn: parent
                width: Math.min(parent.width - 10, parent.height - 10)
                height: width
            }
        }

        // ══════════════════════════════════════════════════════════════════════
        //  AILE DROITE (460 px) — Température Moteur, Performance, Flux Conso
        // ══════════════════════════════════════════════════════════════════════
        ColumnLayout {
            Layout.preferredWidth: 460
            Layout.minimumWidth: 440
            Layout.maximumWidth: 480
            Layout.fillHeight: true
            spacing: 12

            // ── 1. Température Moteur ─────────────────────────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                title: "Température Moteur"
                highlighted: S.UiState.hotEngine
                glowColor: S.UiState.hotEngine ? "#FF1744" : T.StyleManager.accent

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 12

                    ApexGaugeArc {
                        Layout.preferredWidth: 130
                        Layout.preferredHeight: 130
                        label: "Moteur"
                        unit: "°C"
                        value: S.UiState.engineTemp
                        from: 40
                        to: S.UiState.tempMax > 40 ? S.UiState.tempMax : 120
                        warningAt: 0.88
                        baseColor: S.UiState.hotEngine ? "#FF1744" : "#00E676"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: S.UiState.hotEngine ? "SURCHAUFFE !" : (S.UiState.engineTemp < 70 ? "MOTEUR FROID" : "TEMPÉRATURE OPTIMALE")
                            color: S.UiState.hotEngine ? "#FF1744" : (S.UiState.engineTemp < 70 ? "#00E5FF" : "#00E676")
                            font.pixelSize: 13
                            font.weight: Font.Black
                            font.letterSpacing: 1.2
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        ApexMetric {
                            label: "Admission"
                            value: S.UiState.fixed(S.UiState.intakeTemp, 0, "—")
                            unit: "°C"
                            valueSize: 22
                        }
                    }
                }
            }

            // ── 2. Puissance & Couple ─────────────────────────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                title: "Puissance & Charge"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        ApexMetric {
                            label: "Puissance"
                            value: S.UiState.fixed(S.UiState.power, 0, "0")
                            unit: "kW"
                            valueSize: 32
                            valueColor: T.StyleManager.accent
                        }

                        // Barre de progression Puissance
                        Rectangle {
                            Layout.fillWidth: true
                            height: 6
                            radius: 3
                            color: "#0B1522"

                            Rectangle {
                                width: Math.min(1.0, S.UiState.power / 200.0) * parent.width
                                height: parent.height
                                radius: 3
                                color: T.StyleManager.accent
                                Behavior on width { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                            }
                        }
                    }

                    Rectangle { width: 1; Layout.fillHeight: true; color: Qt.rgba(1,1,1,0.08) }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        ApexMetric {
                            label: "Couple"
                            value: S.UiState.fixed(S.UiState.torque, 0, "0")
                            unit: "N·m"
                            valueSize: 32
                            valueColor: "#FFFFFF"
                        }

                        // Barre de progression Couple
                        Rectangle {
                            Layout.fillWidth: true
                            height: 6
                            radius: 3
                            color: "#0B1522"

                            Rectangle {
                                width: Math.min(1.0, S.UiState.torque / 350.0) * parent.width
                                height: parent.height
                                radius: 3
                                color: "#00E5FF"
                                Behavior on width { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                            }
                        }
                    }
                }
            }

            // ── 3. Consommation Instantanée & Dynamique ───────────────────────
            ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Consommation Instantanée"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Instantanée"
                            value: S.UiState.fixed(S.UiState.instantCons, 1, "0,0")
                            unit: "L/100"
                            valueSize: 38
                            valueColor: S.UiState.instantCons > 14 ? "#FFB300" : "#00E676"
                        }

                        ApexMetric {
                            label: "Papillon"
                            value: S.UiState.fixed(S.UiState.throttle, 0, "0")
                            unit: "%"
                            valueSize: 26
                        }
                    }

                    // Barre de débit instantané
                    Rectangle {
                        Layout.fillWidth: true
                        height: 10
                        radius: 5
                        color: "#0A1422"

                        Rectangle {
                            width: Math.min(1.0, Math.max(0, S.UiState.instantCons / 25.0)) * parent.width
                            height: parent.height
                            radius: 5
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "#00E676" }
                                GradientStop { position: 0.6; color: "#FFB300" }
                                GradientStop { position: 1.0; color: "#FF1744" }
                            }
                            Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Pression Turbo"
                            value: S.UiState.fixed(S.UiState.boostPsi, 1, "0,0")
                            unit: "psi"
                            valueSize: 20
                        }

                        ApexMetric {
                            Layout.fillWidth: true
                            label: "Accél. G"
                            value: S.UiState.fixed(S.UiState.gForce, 2, "0,00")
                            unit: "G"
                            valueSize: 20
                        }
                    }
                }
            }
        }
    }
}
