import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "../components"

Item {
    id: root
    anchors.fill: parent

    signal actionRequested(string action)
    signal navigateRequested(string target)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 14

        // Aile gauche : énergie et trajet, lisibles par le conducteur comme le passager.
        ColumnLayout {
            Layout.preferredWidth: 382
            Layout.minimumWidth: 382
            Layout.fillHeight: true
            spacing: 14

            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 280
                title: "ÉNERGIE À BORD"
                highlighted: S.UiState.lowFuel
                glowColor: S.UiState.lowFuel ? "#FFB84D" : T.StyleManager.accent

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 90

                        Column {
                            Layout.fillWidth: true
                            spacing: -3
                            Text {
                                text: Math.round(S.UiState.autonomy)
                                color: "#FFFFFF"
                                font.pixelSize: 58
                                font.weight: Font.Black
                                font.letterSpacing: -2
                            }
                            Text {
                                text: "KM D'AUTONOMIE"
                                color: "#AABACA"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.letterSpacing: 1.7
                            }
                        }

                        Column {
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            spacing: 1
                            Text {
                                anchors.right: parent.right
                                text: S.UiState.fixed(S.UiState.fuelLevel, 1, "—") + " L"
                                color: S.UiState.lowFuel ? "#FFB84D" : T.StyleManager.accent
                                font.pixelSize: 26
                                font.weight: Font.Black
                            }
                            Text {
                                anchors.right: parent.right
                                text: "CARBURANT"
                                color: "#AABACA"
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                font.letterSpacing: 1.4
                            }
                        }
                    }

                    // Jauge large : visible même lorsque les nuances sombres disparaissent.
                    Rectangle {
                        Layout.fillWidth: true
                        height: 22
                        radius: 11
                        color: "#070D13"
                        border.width: 1
                        border.color: "#31465A"

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: 4
                            width: Math.max(12, (parent.width - 8) * Math.max(0, Math.min(1, S.UiState.fuelLevel / Math.max(1, S.UiState.maxFuel))))
                            radius: 7
                            color: S.UiState.lowFuel ? "#FFB84D" : T.StyleManager.accent
                            Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                        }

                        Rectangle {
                            x: parent.width * S.UiState.reservePercentage
                            anchors.verticalCenter: parent.verticalCenter
                            width: 2
                            height: parent.height + 8
                            color: "#FFB84D"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "RÉSERVE"; color: "#FFCB70"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 }
                        Item { Layout.fillWidth: true }
                        Text { text: Math.round(100 * S.UiState.fuelLevel / Math.max(1, S.UiState.maxFuel)) + " %"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#2A3D50" }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Column {
                            Layout.fillWidth: true
                            Text { text: S.UiState.fixed(S.UiState.instantCons, 1, "—"); color: "#FFFFFF"; font.pixelSize: 28; font.bold: true }
                            Text { text: "L/100 INSTANT."; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                        }
                        Rectangle { width: 1; height: 42; color: "#30465A" }
                        Column {
                            Layout.fillWidth: true
                            leftPadding: 22
                            Text { text: S.UiState.fixed(S.UiState.avgConsB, 1, "—"); color: T.StyleManager.accent; font.pixelSize: 28; font.bold: true }
                            Text { text: "L/100 MOYENNE"; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                        }
                    }
                }
            }

            ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "SESSION EN COURS"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0")
                            color: "#FFFFFF"
                            font.pixelSize: 46
                            font.weight: Font.Black
                            font.letterSpacing: -1
                        }
                        Text { text: "KM"; color: "#B3C1CE"; font.pixelSize: 16; font.bold: true; Layout.alignment: Qt.AlignBottom; Layout.bottomMargin: 9 }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            width: stateText.implicitWidth + 22
                            height: 34
                            radius: 17
                            color: S.UiState.sessionState === "PAUSED" ? "#2F2310" : "#10281F"
                            border.width: 1
                            border.color: S.UiState.sessionState === "PAUSED" ? "#FFB84D" : "#54E3A5"
                            Text {
                                id: stateText
                                anchors.centerIn: parent
                                text: S.UiState.sessionState === "PAUSED" ? "EN PAUSE" : "ACTIVE"
                                color: S.UiState.sessionState === "PAUSED" ? "#FFD17D" : "#69EDB2"
                                font.pixelSize: 12
                                font.bold: true
                                font.letterSpacing: 1.3
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ApexMetric { Layout.fillWidth: true; label: "TRIP A"; value: S.UiState.fixed(S.UiState.tripA, 1, "0,0"); unit: "km"; valueSize: 24 }
                        ApexMetric { Layout.fillWidth: true; label: "TRIP B"; value: S.UiState.fixed(S.UiState.tripB, 1, "0,0"); unit: "km"; valueSize: 24 }
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 62
                        radius: 18
                        color: sessionTouch.pressed ? "#1D4C5C" : "#123040"
                        border.width: 1
                        border.color: T.StyleManager.accent

                        Row {
                            anchors.centerIn: parent
                            spacing: 12
                            Rectangle { width: 10; height: 10; radius: 5; color: T.StyleManager.accent; anchors.verticalCenter: parent.verticalCenter }
                            Text {
                                text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE LE TRAJET" : "TERMINER LE TRAJET"
                                color: "#FFFFFF"
                                font.pixelSize: 15
                                font.bold: true
                                font.letterSpacing: 1.7
                            }
                        }
                        MouseArea {
                            id: sessionTouch
                            anchors.fill: parent
                            onClicked: {
                                if (S.UiState.sessionState === "PAUSED") bridge.resumeTripSession()
                                else root.actionRequested("end_trip")
                            }
                        }
                    }
                }
            }
        }

        ApexVelocityCore {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 760
        }

        // Aile droite : santé mécanique et contexte routier.
        ColumnLayout {
            Layout.preferredWidth: 410
            Layout.minimumWidth: 410
            Layout.fillHeight: true
            spacing: 14

            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 326
                title: "ÉQUILIBRE MÉCANIQUE"
                highlighted: S.UiState.hotEngine
                glowColor: S.UiState.hotEngine ? "#FF5964" : T.StyleManager.accent

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        Column {
                            Layout.fillWidth: true
                            spacing: -2
                            Row {
                                spacing: 6
                                Text {
                                    text: Math.round(S.UiState.engineTemp)
                                    color: S.UiState.hotEngine ? "#FF6670" : "#FFFFFF"
                                    font.pixelSize: 66
                                    font.weight: Font.Black
                                    font.letterSpacing: -2
                                }
                                Text { text: "°C"; color: S.UiState.hotEngine ? "#FF6670" : T.StyleManager.accent; font.pixelSize: 25; font.bold: true; anchors.baseline: parent.children[0].baseline }
                            }
                            Text {
                                text: S.UiState.hotEngine ? "TEMPÉRATURE CRITIQUE" : (S.UiState.engineTemp < 70 ? "MISE EN TEMPÉRATURE" : "PLAGE OPTIMALE")
                                color: S.UiState.hotEngine ? "#FF7881" : (S.UiState.engineTemp < 70 ? "#75D9FF" : "#69EDB2")
                                font.pixelSize: 13
                                font.bold: true
                                font.letterSpacing: 1.2
                            }
                        }

                        // Anneau simple, épais et visible.
                        Canvas {
                            Layout.preferredWidth: 112
                            Layout.preferredHeight: 112
                            property real value: S.UiState.engineTemp
                            onValueChanged: requestPaint()
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.reset()
                                var c = width / 2
                                var ratio = Math.max(0, Math.min(1, (value - S.UiState.tempMin) / Math.max(1, S.UiState.tempMax - S.UiState.tempMin)))
                                ctx.lineCap = "round"
                                ctx.lineWidth = 11
                                ctx.beginPath(); ctx.arc(c, c, c - 12, Math.PI * 0.72, Math.PI * 2.28); ctx.strokeStyle = "#172636"; ctx.stroke()
                                ctx.beginPath(); ctx.arc(c, c, c - 12, Math.PI * 0.72, Math.PI * (0.72 + ratio * 1.56)); ctx.strokeStyle = S.UiState.hotEngine ? "#FF5964" : T.StyleManager.accent; ctx.stroke()
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#2A3D50" }

                    Repeater {
                        model: [
                            { label: "CHARGE MOTEUR", value: S.UiState.engineLoad, text: S.UiState.fixed(S.UiState.engineLoad, 0, "0") + " %", color: T.StyleManager.accent },
                            { label: "PUISSANCE", value: 100 * S.UiState.power / Math.max(1, S.UiState.maxPowerKw), text: S.UiState.fixed(S.UiState.powerHp, 0, "0") + " / " + S.UiState.fixed(S.UiState.maxPowerHp, 0, "0") + " ch", color: "#6EE8FF" },
                            { label: "FORCE LATÉRALE", value: Math.min(100, Math.abs(S.UiState.gForce) * 100), text: S.UiState.fixed(S.UiState.gForce, 2, "0,00") + " G", color: "#FFCA68" }
                        ]
                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: modelData.label; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 }
                                Item { Layout.fillWidth: true }
                                Text { text: modelData.text; color: "#FFFFFF"; font.pixelSize: 15; font.bold: true }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 8; radius: 4; color: "#101C27"
                                Rectangle {
                                    width: Math.max(6, parent.width * modelData.value / 100)
                                    height: parent.height; radius: parent.radius; color: modelData.color
                                    Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                }
                            }
                        }
                    }
                }
            }

            ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "ROUTE & ENVIRONNEMENT"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Column {
                            Layout.fillWidth: true
                            Text { text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—") + "°"; color: "#FFFFFF"; font.pixelSize: 40; font.bold: true }
                            Text { text: "EXTÉRIEUR"; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.3 }
                        }
                        Column {
                            Layout.fillWidth: true
                            Text { text: S.UiState.fixed(S.UiState.odometer, 0, "—"); color: "#FFFFFF"; font.pixelSize: 27; font.bold: true }
                            Text { text: "ODOMÈTRE KM"; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.3 }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#2A3D50" }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 16
                        color: S.UiState.attentionVehicle ? "#301920" : "#0D1B22"
                        border.width: 1
                        border.color: S.UiState.attentionVehicle ? "#FF6670" : "#2B4B59"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            Rectangle {
                                width: 14; height: 14; radius: 7
                                color: S.UiState.attentionVehicle ? "#FF6670" : "#54E3A5"
                            }
                            Column {
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    text: S.UiState.attentionVehicle ? "ATTENTION REQUISE" : "VÉHICULE PRÊT"
                                    color: "#FFFFFF"
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.letterSpacing: 1.2
                                }
                                Text {
                                    text: S.UiState.attentionVehicle ? "Vérifiez ceinture et ouvrants" : "Tous les systèmes sont opérationnels"
                                    color: "#B6C4D0"
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
