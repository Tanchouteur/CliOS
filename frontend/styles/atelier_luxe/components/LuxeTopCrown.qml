import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 1920
    height: 48

    signal openSettingsRequested()

    // 1. Gauche : Horloge de bord & Température extérieure (Sans aucun émoji)
    RowLayout {
        anchors.left: parent.left
        anchors.leftMargin: 30
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        Text {
            text: Qt.formatTime(new Date(), "hh:mm")
            color: "#FFFFFF"
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 19
            font.weight: Font.Bold
            font.letterSpacing: 1.5
        }

        Rectangle { width: 1.5; height: 16; color: "#223348" }

        RowLayout {
            spacing: 4
            Text {
                text: "EXT."
                color: "#BAC8D9"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 1
            }
            Text {
                text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—") + " °C"
                color: "#FFFFFF"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 15
                font.weight: Font.Bold
            }
        }
    }

    // 2. Centre : Rangée de 11 Voyants Bijoux Ciselés (Haute lisibilité)
    RowLayout {
        anchors.centerIn: parent
        spacing: 7

        Repeater {
            model: [
                { id: "turn_left", label: "◀", color: T.StyleManager.success, active: S.UiState.boolValue(S.UiState.vehicle.turn_left) || S.UiState.boolValue(S.UiState.vehicle.indicator_left) },
                { id: "turn_right", label: "▶", color: T.StyleManager.success, active: S.UiState.boolValue(S.UiState.vehicle.turn_right) || S.UiState.boolValue(S.UiState.vehicle.indicator_right) },
                { id: "lights", label: "FEU", color: T.StyleManager.success, active: S.UiState.boolValue(S.UiState.vehicle.lights) || S.UiState.boolValue(S.UiState.vehicle.pos_lights) || S.UiState.boolValue(S.UiState.vehicle.low_beam) },
                { id: "high_beam", label: "ROUTE", color: "#3B82F6", active: S.UiState.boolValue(S.UiState.vehicle.high_beam) },
                { id: "stop", label: "STOP", color: T.StyleManager.danger, active: S.UiState.boolValue(S.UiState.vehicle.parking_brake) || S.UiState.boolValue(S.UiState.vehicle.brake_warning) },
                { id: "unbelted", label: "CEINT", color: T.StyleManager.danger, active: S.UiState.boolValue(S.UiState.vehicle.driver_unbelted) },
                { id: "door", label: "PORTE", color: T.StyleManager.warning, active: S.UiState.doorOpen },
                { id: "oil", label: "HUILE", color: T.StyleManager.danger, active: S.UiState.boolValue(S.UiState.vehicle.oil_warning) },
                { id: "battery", label: "BAT", color: T.StyleManager.danger, active: S.UiState.boolValue(S.UiState.vehicle.battery_warning) },
                { id: "abs", label: "ABS", color: T.StyleManager.warning, active: S.UiState.boolValue(S.UiState.vehicle.abs_warning) },
                { id: "esp", label: "ESP", color: T.StyleManager.warning, active: S.UiState.boolValue(S.UiState.vehicle.esp_warning) },
                { id: "engine", label: "MOT", color: T.StyleManager.warning, active: S.UiState.boolValue(S.UiState.vehicle.engine_warning) }
            ]

            Rectangle {
                width: modelData.label.length > 2 ? 40 : 28
                height: 24
                radius: 5
                color: modelData.active ? Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.28) : "#080C14"
                border.width: 1
                border.color: modelData.active ? modelData.color : "#162030"

                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: modelData.active ? modelData.color : "#3A4D64"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    font.letterSpacing: 0.6
                }
            }
        }
    }

    // 3. Droite : Stockage & Bouton Réglages Haute Précision
    RowLayout {
        anchors.right: parent.right
        anchors.rightMargin: 30
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14

        // Stockage USB
        RowLayout {
            spacing: 6
            Rectangle {
                width: 7; height: 7; radius: 3.5
                color: S.UiState.usbConnected ? T.StyleManager.success : "#4A5B6E"
            }
            Text {
                text: "USB " + S.UiState.fixed(S.UiState.storage.free_space_mb, 0, "—") + " MB"
                color: "#FFFFFF"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 13
                font.weight: Font.Bold
            }
        }

        Rectangle { width: 1.5; height: 16; color: "#223348" }

        // Bouton Réglages Ciselé
        Rectangle {
            width: 38
            height: 38
            radius: 19
            color: touchSettings.pressed ? Qt.rgba(1, 1, 1, 0.25) : "#142032"
            border.width: 1.2
            border.color: "#2C3F58"

            Text {
                anchors.centerIn: parent
                text: "⚙"
                color: "#FFFFFF"
                font.pixelSize: 17
            }

            MouseArea {
                id: touchSettings
                anchors.fill: parent
                onClicked: root.openSettingsRequested()
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
