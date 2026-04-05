import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../style" as T

Item {
    id: root

    property var vData: bridge.data !== undefined ? bridge.data : {}
    property var vStats: bridge.stats !== undefined ? bridge.stats : {}

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
                    width: parent.width * 0.6 // Plus étroite pour l'effet de superposition
                    height: parent.height * ((vData.accel_2 !== undefined ? vData.accel_2 : 0) / 237)
                    color: T.Theme.mainLight
                    opacity: 0.8
                    radius: 4

                    // Petit effet de lueur pour la barre réelle
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
                        // Affiche "Pied % / Réel %"
                        text: Math.round(vData.accel_pos || 0) + " / " + Math.round(vData.accel_real || 0) + "%"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }
        }

        // ─── CENTRE : G-METER ───
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "transparent"
            z: 2

            // Cible du G-Meter
            Rectangle {
                anchors.centerIn: parent
                width: 250; height: 250; radius: 125
                color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 2

                // Lignes de graduation
                Rectangle { width: parent.width; height: 1; color: Qt.rgba(1,1,1,0.1); anchors.centerIn: parent }
                Rectangle { width: 1; height: parent.height; color: Qt.rgba(1,1,1,0.1); anchors.centerIn: parent }

                // La bille (Bille G)
                Rectangle {
                    id: gBall
                    width: 24; height: 24; radius: 12; color: T.Theme.main

                    x: (parent.width / 2) - 12
                    // Sécurité anti-undefined pour l'axe Y
                    y: (parent.height / 2) - 12 - ((vStats.g_force !== undefined ? vStats.g_force : 0.0) * 100)

                    Behavior on y { NumberAnimation { duration: 100 } }
                }

                Text {
                    anchors.bottom: parent.top; anchors.bottomMargin: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    // Sécurité anti-undefined pour le texte
                    text: (vStats.g_force !== undefined ? vStats.g_force : 0.0).toFixed(2) + " G"
                    color: "white"; font.pixelSize: 24; font.bold: true
                }
            }
        }

        // ─── DROITE : COUPLE & MOTEUR ───
        ColumnLayout {
            Layout.preferredWidth: 200
            spacing: 20

            // Torque (Double Jauge Verticale : Demande vs ECU)
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 12; color: T.Theme.bgDimmed
                clip: true

                // 1. BARRE FOND : Couple demandé (Driver Request)
                Rectangle {
                    id: torqueReqBar
                    anchors.bottom: parent.bottom
                    width: parent.width
                    // Base de calcul sur 300 Nm (à ajuster si ton moteur est plus coupleux)
                    height: parent.height * (Math.min(vData.driver_torque_request || 0, 300) / 300)
                    color: T.Theme.main
                    opacity: 0.3

                    Behavior on height { NumberAnimation { duration: 150 } }
                }

                // 2. BARRE CENTRALE : Couple réel (ECU Torque)
                Rectangle {
                    id: torqueEcuBar
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width * 0.5
                    height: parent.height * (Math.min(vData.torque_ecu || 0, 300) / 300)
                    color: T.Theme.mainLight
                    opacity: 0.9
                    radius: 4

                    // Petit dégradé pour l'aspect "énergie"
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: T.Theme.mainLight }
                        GradientStop { position: 1.0; color: Qt.lighter(T.Theme.mainLight, 1.2) }
                    }

                    Behavior on height { NumberAnimation { duration: 100 } }
                }

                // 3. AFFICHAGE DES VALEURS
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    z: 2

                    Text {
                        text: "TORQUE"
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Valeur ECU (La plus importante)
                    Text {
                        text: Math.round(vData.torque_ecu || 0)
                        color: "white"
                        font.pixelSize: 34
                        font.bold: true
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Petit rappel de la demande en dessous
                    Text {
                        text: "REQ: " + Math.round(vData.driver_torque_request || 0) + " Nm"
                        color: Qt.rgba(1,1,1,0.7)
                        font.pixelSize: 14
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Engine Load (Basé sur Torque vs Max)
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 120
                radius: 12; color: T.Theme.bgDimmed

                Text {
                    anchors.centerIn: parent
                    text: "LOAD"
                    color: T.Theme.unselected
                }
            }
        }
    }
}