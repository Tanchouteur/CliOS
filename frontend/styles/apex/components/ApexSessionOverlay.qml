import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "./"

// Overlay pause/fin de trajet
Item {
    id: root
    anchors.fill: parent
    signal actionRequested(string action)

    visible: S.UiState.sessionState === "PAUSED" || S.UiState.sessionState === "ENDED"
    opacity: visible ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }

    // Fond flouté
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.04, 0.09, 0.88)
    }

    // Carte centrale
    Rectangle {
        anchors.centerIn: parent
        width: 900; height: 360
        radius: 24
        color: "#0D1A2A"
        border.width: 1
        border.color: S.UiState.sessionState === "ENDED"
            ? Qt.rgba(0.0, 0.9, 0.47, 0.4)
            : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.4)

        // Ligne supérieure
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2; radius: parent.radius
            color: S.UiState.sessionState === "ENDED" ? "#00E676" : T.StyleManager.accent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 36
            spacing: 20

            // Titre
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: S.UiState.sessionState === "ENDED" ? "TRAJET TERMINÉ" : "SESSION EN PAUSE"
                color: "#FFFFFF"
                font.pixelSize: 20
                font.weight: Font.Black
                font.letterSpacing: 4
            }

            // Métriques
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Repeater {
                    model: [
                        { label: "Distance",  value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.distance_km : 0, 1, "0,0"),    unit: "km" },
                        { label: "Carburant", value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.session_fuel_l : 0, 2, "0,00"), unit: "L"  },
                        { label: "Coût",      value: S.UiState.fixed(S.UiState.trip ? S.UiState.trip.session_cost : 0, 2, "0,00"),   unit: "€"  }
                    ]
                    delegate: Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Column {
                            anchors.centerIn: parent
                            spacing: 6

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label.toUpperCase()
                                color: Qt.rgba(1, 1, 1, 0.32)
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                font.letterSpacing: 2.5
                            }
                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 6
                                Text {
                                    text: modelData.value
                                    color: "#FFFFFF"
                                    font.pixelSize: 46
                                    font.weight: Font.Black
                                    font.letterSpacing: -1
                                }
                                Text {
                                    text: modelData.unit
                                    color: Qt.rgba(1, 1, 1, 0.38)
                                    font.pixelSize: 20
                                    anchors.baseline: parent.children[0] ? parent.children[0].baseline : undefined
                                }
                            }
                        }

                        // Séparateur vertical (sauf sur le dernier)
                        Rectangle {
                            visible: index < 2
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1; height: 60
                            color: Qt.rgba(1, 1, 1, 0.07)
                        }
                    }
                }
            }

            // Boutons (PAUSED seulement)
            RowLayout {
                visible: S.UiState.sessionState === "PAUSED"
                Layout.alignment: Qt.AlignHCenter
                spacing: 16

                Rectangle {
                    width: 260; height: 52; radius: 14
                    color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.15)
                    border.width: 1; border.color: T.StyleManager.accent
                    Text {
                        anchors.centerIn: parent; text: "CONTINUER"
                        color: T.StyleManager.accent
                        font.pixelSize: 14; font.weight: Font.Black; font.letterSpacing: 2
                    }
                    MouseArea {
                        anchors.fill: parent
                        onPressed: parent.opacity = 0.7; onReleased: parent.opacity = 1.0
                        onClicked: bridge.resumeTripSession()
                    }
                }

                Rectangle {
                    width: 300; height: 52; radius: 14
                    color: Qt.rgba(1.0, 0.1, 0.1, 0.12)
                    border.width: 1; border.color: Qt.rgba(1.0, 0.2, 0.1, 0.5)
                    Text {
                        anchors.centerIn: parent; text: "TERMINER LE TRAJET"
                        color: "#FF4444"
                        font.pixelSize: 14; font.weight: Font.Black; font.letterSpacing: 2
                    }
                    MouseArea {
                        anchors.fill: parent
                        onPressed: parent.opacity = 0.7; onReleased: parent.opacity = 1.0
                        onClicked: root.actionRequested("end_trip")
                    }
                }
            }

            // Message fin
            Text {
                visible: S.UiState.sessionState === "ENDED"
                Layout.alignment: Qt.AlignHCenter
                text: "✓  Données sauvegardées"
                color: "#00E676"
                font.pixelSize: 18
                font.weight: Font.Bold
                font.letterSpacing: 1
            }
        }
    }
}
