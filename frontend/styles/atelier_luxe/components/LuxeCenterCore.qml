import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 900
    height: 560

    signal actionRequested(string action)

    // Boîtier principal de la console centrale en titane usiné
    Rectangle {
        anchors.fill: parent
        radius: 18
        color: "#0B111A"
        border.width: 1.5
        border.color: "#1E2C3E"

        // Liseré spéculaire supérieur
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            height: 1
            color: Qt.rgba(1, 1, 1, 0.15)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            // =================================================================
            // 1. EN-TÊTE HORLOGER : HEURE PRÉCISION, DATE & TEMPÉRATURE (SANS ÉMOJI)
            // =================================================================
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                radius: 12
                color: "#0E1624"
                border.width: 1
                border.color: "#182436"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 16

                    // Horloge numérique de manufacture
                    Text {
                        text: Qt.formatTime(new Date(), "hh:mm:ss")
                        color: "#FFFFFF"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 34
                        font.weight: Font.Bold
                        font.letterSpacing: 2
                    }

                    // Séparateur vertical
                    Rectangle { width: 1.5; Layout.fillHeight: true; color: "#223348" }

                    // Date en toutes lettres (Français)
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: Qt.formatDate(new Date(), "dddd d MMMM yyyy").toUpperCase()
                            color: T.StyleManager.accent
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            font.letterSpacing: 1.5
                        }
                        Text {
                            text: S.UiState.profileName() + " · CHÂSSIS ACTIF"
                            color: "#BAC8D9"
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1
                        }
                    }

                    // Séparateur vertical
                    Rectangle { width: 1.5; Layout.fillHeight: true; color: "#223348" }

                    // Température extérieure haute précision
                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: "TEMPÉRATURE EXT."
                            color: "#8A9BAF"
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                        }
                        RowLayout {
                            spacing: 4
                            Text {
                                text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—")
                                color: "#FFFFFF"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 22
                                font.weight: Font.Bold
                            }
                            Text {
                                text: "°C"
                                color: T.StyleManager.accent
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                        }
                    }
                }
            }

            // =================================================================
            // 2. CORPS PRINCIPAL : MODULES PHYSIQUES DENSES
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                // -------------------------------------------------------------
                // MODULE GAUCHE : BILAN DE SESSION & ÉNERGIE
                // -------------------------------------------------------------
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 14
                    color: "#0E1624"
                    border.width: 1
                    border.color: S.UiState.tripActive ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.4) : "#182436"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        // En-tête du module
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: S.UiState.tripActive ? T.StyleManager.accent : "#8A9BAF"
                            }
                            Text {
                                text: "SESSION DE CONDUITE"
                                color: S.UiState.tripActive ? T.StyleManager.accent : "#BAC8D9"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: S.UiState.sessionState
                                color: S.UiState.tripActive ? T.StyleManager.success : "#8A9BAF"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Bold
                            }
                        }

                        // Distance parcourue (Grand Format)
                        Text {
                            text: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0") + " km"
                            color: "#FFFFFF"
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 42
                            font.weight: Font.Bold
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#1E2C40" }

                        // Métriques de consommation & Coût
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            // Carburant consommé
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: "CARBURANT"; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Text { text: S.UiState.fixed(S.UiState.tripFuelLiters, 2, "0,00") + " L"; color: "#FFFFFF"; font.pixelSize: 22; font.weight: Font.Bold }
                            }

                            Rectangle { width: 1; Layout.fillHeight: true; color: "#1E2C40" }

                            // Coût estimé
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: "COÛT ESTIMÉ"; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Text { text: S.UiState.fixed(S.UiState.tripCost, 2, "0,00") + " €"; color: T.StyleManager.accent; font.pixelSize: 22; font.weight: Font.Bold }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#1E2C40" }

                        // Éco-conduite : décélération sans accélérateur
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: "DÉCÉLÉRATION SANS GAZ"; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Text { text: S.UiState.fixed(S.UiState.decelerationWithoutThrottleKm, 1, "0,0") + " km"; color: T.StyleManager.success; font.pixelSize: 20; font.weight: Font.Bold }
                            }
                            ColumnLayout {
                                spacing: 2
                                Text { text: "AGRESSIVITÉ"; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Text { text: S.UiState.fixed(S.UiState.aggressivityPct, 0, "0") + " %"; color: "#FFFFFF"; font.pixelSize: 20; font.weight: Font.Bold }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // MODULE DROIT : TRIP B, ACCÉLÉRATION G-FORCE & MAINTENANCE
                // -------------------------------------------------------------
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 14
                    color: "#0E1624"
                    border.width: 1
                    border.color: "#182436"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        // En-tête Trip B avec bouton Reset physique
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "TRIP B JOURNALIER"
                                color: "#BAC8D9"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                width: 72
                                height: 28
                                radius: 6
                                color: Qt.rgba(1.0, 0.3, 0.35, 0.22)
                                border.width: 1
                                border.color: T.StyleManager.danger

                                Text {
                                    anchors.centerIn: parent
                                    text: "RESET B"
                                    color: T.StyleManager.danger
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.actionRequested("reset_b")
                                }
                            }
                        }

                        // Valeurs Trip B & Consommation Moyenne B
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: S.UiState.fixed(S.UiState.tripB, 1, "0,0") + " km"
                                    color: "#FFFFFF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 32
                                    font.weight: Font.Bold
                                }
                                Text { text: "DISTANCE TRIP B"; color: "#8A9BAF"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                            }

                            Rectangle { width: 1; Layout.fillHeight: true; color: "#1E2C40" }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: S.UiState.fixed(S.UiState.avgConsB, 1, "0,0") + " L"
                                    color: T.StyleManager.accent
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 32
                                    font.weight: Font.Bold
                                }
                                Text { text: "MOYENNE / 100 KM"; color: "#8A9BAF"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#1E2C40" }

                        // G-Force Latérale & Accélération Dynamique
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "ACCÉLÉRATION LONG."; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: S.UiState.fixed(S.UiState.longitudinalG, 2, "0.00") + " G"
                                    color: "#FFFFFF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 18
                                    font.weight: Font.Bold
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 6
                                radius: 3
                                color: "#182436"

                                Rectangle {
                                    width: parent.width * Math.min(1.0, Math.max(0.0, Math.abs(S.UiState.longitudinalG) / 1.5))
                                    height: parent.height
                                    radius: 3
                                    color: T.StyleManager.accent
                                    Behavior on width { NumberAnimation { duration: 100 } }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#1E2C40" }

                        // Rappel de maintenance & révision
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: "RÉVISION ENTRETIEN"; color: "#8A9BAF"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Text {
                                    text: S.UiState.fixed(S.UiState.kmBeforeService, 0, "—") + " km restants"
                                    color: S.UiState.serviceWarning ? T.StyleManager.warning : "#FFFFFF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 16
                                    font.weight: Font.Bold
                                }
                            }
                            Rectangle {
                                width: 10; height: 10; radius: 5
                                color: S.UiState.serviceWarning ? T.StyleManager.warning : T.StyleManager.success
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {}
    }
}
