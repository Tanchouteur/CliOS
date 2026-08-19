import QtQuick
import QtQuick.Layouts
import "../components"
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    function wheelColor(slip, locked) {
        return locked ? T.StyleManager.danger : (slip ? T.StyleManager.warning : T.StyleManager.success)
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        GtCard {
            Layout.preferredWidth: 300; Layout.minimumWidth: 300; Layout.maximumWidth: 300; Layout.fillHeight: true; title: "Commandes"
            ColumnLayout {
                anchors.fill: parent; spacing: 14
                GtMetric { Layout.fillWidth: true; label: "Accélérateur demandé"; value: S.UiState.fixed(S.UiState.throttle, 0, "0"); unit: "%" }
                GtProgress { Layout.fillWidth: true; height: 12; value: S.UiState.throttle }
                GtMetric { Layout.fillWidth: true; label: "Accélérateur réel"; value: S.UiState.fixed(S.UiState.accelComputed, 0, "0"); unit: "%" }
                GtProgress { Layout.fillWidth: true; height: 12; value: S.UiState.accelComputed; to: 237; fillColor: T.StyleManager.info }
                RowLayout {
                    Layout.fillWidth: true
                    GtMetric { Layout.fillWidth: true; label: "Embray."; value: S.UiState.clutchPressed ? "ACTIF" : "LIBRE"; valueSize: 23 }
                    GtMetric { Layout.fillWidth: true; label: "Frein"; value: S.UiState.brakePressed ? "ACTIF" : "LIBRE"; valueSize: 23; valueColor: S.UiState.brakePressed ? T.StyleManager.danger : T.StyleManager.text }
                }
            }
        }

        GtCard {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Accélération longitudinale"
            Item {
                anchors.fill: parent
                Rectangle {
                    width: 40; height: parent.height - 40
                    anchors.centerIn: parent
                    radius: 20
                    color: T.StyleManager.gaugeTrack
                    Rectangle { width: parent.width; height: 2; anchors.centerIn: parent; color: T.StyleManager.textSecondary }
                    Rectangle {
                        width: 30; height: 30; radius: 15
                        x: 5
                        y: Math.max(5, Math.min(parent.height - height - 5,
                           parent.height / 2 - height / 2 - S.UiState.longitudinalG * parent.height * 0.34))
                        color: T.StyleManager.accent
                        Behavior on y { NumberAnimation { duration: T.StyleManager.durationFast } }
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    text: S.UiState.fixed(S.UiState.longitudinalG, 2, "0,00") + " G LONG."
                    color: T.StyleManager.text
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                }
                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "FREINAGE"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "ACCÉLÉRATION"; color: T.StyleManager.textSecondary; font.pixelSize: 16 }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 370; Layout.minimumWidth: 370; Layout.maximumWidth: 370; Layout.fillHeight: true; spacing: 14
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Couple"
                GtMetric { anchors.centerIn: parent; width: parent.width; label: "Demande conducteur"; value: S.UiState.fixed(S.UiState.driverTorqueRequest, 0, "0"); unit: "%"; alignment: Text.AlignHCenter }
            }
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Dynamique des roues"
                GridLayout {
                    anchors.centerIn: parent; columns: 2; columnSpacing: 54; rowSpacing: 16
                    Repeater {
                        model: [
                            {name:"AVG", slip:S.UiState.wheelSlipFl, lock:S.UiState.wheelLockFl},
                            {name:"AVD", slip:S.UiState.wheelSlipFr, lock:S.UiState.wheelLockFr},
                            {name:"ARG", slip:S.UiState.wheelSlipRl, lock:S.UiState.wheelLockRl},
                            {name:"ARD", slip:S.UiState.wheelSlipRr, lock:S.UiState.wheelLockRr}
                        ]
                        Rectangle {
                            width: 90; height: 50; radius: T.StyleManager.radiusSmall
                            color: Qt.rgba(root.wheelColor(modelData.slip, modelData.lock).r, root.wheelColor(modelData.slip, modelData.lock).g, root.wheelColor(modelData.slip, modelData.lock).b, 0.14)
                            border.width: 2; border.color: root.wheelColor(modelData.slip, modelData.lock)
                            Text { anchors.centerIn: parent; text: modelData.name; color: parent.border.color; font.pixelSize: 17; font.bold: true }
                        }
                    }
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.preferredHeight: 112; title: "Bruit cabine"
                GtMetric { anchors.centerIn: parent; width: parent.width; label: "Niveau mesuré"; value: S.UiState.fixed(S.UiState.cabinDbSpl, 0, "—"); unit: "dB"; alignment: Text.AlignHCenter; valueSize: 27 }
            }
        }
    }
}
