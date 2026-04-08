import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../style" as T
Item {
    id: root

    property var vData: bridge.data !== undefined ? bridge.data : {}
    property var vStats: bridge.stats !== undefined ? bridge.stats : {}

    function getTireColor(isSlipping, isLocked) {
        if (isLocked) return "#ff0000"    // Rouge = Blocage
        if (isSlipping) return "#0088ff"  // Bleu = Patinage
        return Qt.rgba(1, 1, 1, 0.05)     // Gris transparent = Normal
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 40

        // ─── GAUCHE : CONTRÔLES PILOTE (PÉDALES) ───
        ColumnLayout {
            Layout.preferredWidth: 200
            spacing: 20

            // Embrayage (ON/OFF)
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 60
                radius: 8; color: T.Theme.bgDimmed
                border.color: vData.clutch ? "white" : Qt.rgba(1,1,1,0.1)
                border.width: 2
                Text {
                    anchors.centerIn: parent
                    text: "CLUTCH"
                    color: vData.clutch ? "white" : T.Theme.unselected
                    font.bold: true
                }
            }

            // Frein (ON/OFF)
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 60
                radius: 8; color: vData.brake ? Qt.rgba(1,0,0,0.3) : T.Theme.bgDimmed
                border.color: vData.brake ? "#ff0000" : Qt.rgba(1,1,1,0.1)
                border.width: 2
                Text {
                    anchors.centerIn: parent
                    text: "BRAKE"
                    color: vData.brake ? "white" : T.Theme.unselected
                    font.bold: true
                }
            }

            // Accélérateur (Double Jauge : Pied vs Réel)
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 8; color: T.Theme.bgDimmed
                clip: true

                // 1. BARRE FOND : Position du pied (Demande Pilote)
                Rectangle {
                    id: pedalBar
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: parent.height * ((vData.accel_pos !== undefined ? vData.accel_pos : 0) / 100)
                    color: T.Theme.main
                    opacity: 0.4

                    Behavior on height { NumberAnimation { duration: 100 } }
                }

                // 2. BARRE SUPERPOSÉE : Position réelle
                Rectangle {
                    id: realBar
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width * 0.6
                    height: parent.height * ((vData.accel_computed !== undefined ? vData.accel_computed : 0) / 237)
                    color: T.Theme.mainLight
                    opacity: 0.8
                    radius: 4
                    layer.enabled: true

                    Behavior on height { NumberAnimation { duration: 80 } }
                }

                // 3. TEXTES INFORMATIFS
                Column {
                    anchors.centerIn: parent
                    spacing: 5
                    z: 2

                    Text {
                        text: "THROTTLE"
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: Math.round(vData.accel_pos || 0) + " / " + Math.round(vData.accel_computed || 0) + "%"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }
        }

        // ─── CENTRE : G-METER & DYNAMIQUES ROUES ───
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "transparent"
            z: 2


            // -- FL (Front Left) : BIEN À GAUCHE --
            Column {
                anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 10
                spacing: 5
                Text { text: "FL"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
                Rectangle {
                    width: 24; height: 100; radius: 4
                    border.color: Qt.rgba(1, 1, 1, 0.2); border.width: 1
                    color: getTireColor(vData.wheel_slip_fl, vData.wheel_lock_fl)
                    Behavior on color { ColorAnimation { duration: 100 } }
                }
            }

            // -- FR (Front Right) : BIEN À DROITE --
            Column {
                anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 10
                spacing: 5
                Text { text: "FR"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
                Rectangle {
                    width: 24; height: 100; radius: 4
                    border.color: Qt.rgba(1, 1, 1, 0.2); border.width: 1
                    color: getTireColor(vData.wheel_slip_fr, vData.wheel_lock_fr)
                    Behavior on color { ColorAnimation { duration: 100 } }
                }
            }

            // -- RL (Rear Left) : BIEN À GAUCHE --
            Column {
                anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 10
                spacing: 5
                Rectangle {
                    width: 24; height: 100; radius: 4
                    border.color: Qt.rgba(1, 1, 1, 0.2); border.width: 1
                    color: getTireColor(vData.wheel_slip_rl, vData.wheel_lock_rl)
                    Behavior on color { ColorAnimation { duration: 100 } }
                }
                Text { text: "RL"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
            }

            // -- RR (Rear Right) : BIEN À DROITE --
            Column {
                anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 10
                spacing: 5
                Rectangle {
                    width: 24; height: 100; radius: 4
                    border.color: Qt.rgba(1, 1, 1, 0.2); border.width: 1
                    color: getTireColor(vData.wheel_slip_rr, vData.wheel_lock_rr)
                    Behavior on color { ColorAnimation { duration: 100 } }
                }
                Text { text: "RR"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
            }

            // -- Cible du G-Meter (Au centre) --
            Rectangle {
                anchors.centerIn: parent
                width: 250; height: 250; radius: 125
                color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 2

                Rectangle { width: parent.width; height: 1; color: Qt.rgba(1,1,1,0.1); anchors.centerIn: parent }
                Rectangle { width: 1; height: parent.height; color: Qt.rgba(1,1,1,0.1); anchors.centerIn: parent }

                Rectangle {
                    id: gBall
                    width: 24; height: 24; radius: 12; color: T.Theme.main
                    x: (parent.width / 2) - 12
                    y: (parent.height / 2) - 12 - ((vStats.g_force !== undefined ? vStats.g_force : 0.0) * 100)
                    Behavior on y { NumberAnimation { duration: 100 } }
                }

                Text {
                    anchors.bottom: parent.top; anchors.bottomMargin: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: (vStats.g_force !== undefined ? vStats.g_force : 0.0).toFixed(2) + " G"
                    color: "white"; font.pixelSize: 24; font.bold: true
                }
            }
        }

        // ─── DROITE : COUPLE & MOTEUR ───
        ColumnLayout {
            Layout.preferredWidth: 200
            spacing: 20

            // Torque
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 12; color: T.Theme.bgDimmed
                clip: true
                property real maxTorque: 155

                Rectangle {
                    id: torqueAvailableBar
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: parent.height * (Math.min(vData.torque_available || 0, parent.maxTorque) / parent.maxTorque)
                    color: T.Theme.main
                    opacity: 0.25
                    Behavior on height { NumberAnimation { duration: 150 } }
                }

                Rectangle {
                    id: torqueActualBar
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width * 0.5
                    height: parent.height * (vData.driver_torque_request / 300)
                    color: T.Theme.mainLight
                    opacity: 0.9
                    radius: 4
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: T.Theme.mainLight }
                        GradientStop { position: 1.0; color: Qt.lighter(T.Theme.mainLight, 1.2) }
                    }
                    Behavior on height { NumberAnimation { duration: 100 } }
                }

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    z: 2
                    Text { text: "TORQUE"; color: "white"; font.pixelSize: 12; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                    Text { text: Math.round(vData.driver_torque_request !== undefined ? vData.driver_torque_request : -100); color: "white"; font.pixelSize: 34; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                    Text { text: "MAX: " + Math.round(vData.torque_available || 0) + " Nm"; color: Qt.rgba(1,1,1,0.7); font.pixelSize: 14; Layout.alignment: Qt.AlignHCenter }
                }
            }

            // Engine Load
            /*Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 120
                radius: 12; color: T.Theme.bgDimmed
                clip: true

                Rectangle {
                    anchors.left: parent.left; anchors.bottom: parent.bottom
                    height: parent.height
                    width: parent.width * ((vData.engine_load !== undefined ? vData.engine_load : 0) / 100)
                    color: "white"; opacity: 0.05
                    Behavior on width { NumberAnimation { duration: 200 } }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 5
                    Text { text: "LOAD"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: Math.round(vData.engine_load || 0) + "%"; color: "white"; font.bold: true; font.pixelSize: 24; anchors.horizontalCenter: parent.horizontalCenter }
                }
            }*/
        }
    }
}