import QtQuick
import QtQuick.Shapes
import "../components"
import "../style"

Item {
    id: root

    // --- NOUVEAU : Écoute directe du service Python ---
    property string sessionState: bridge.data !== undefined && bridge.data.session_state !== undefined ? bridge.data.session_state : "IDLE"

    Rectangle {
        anchors.fill: parent
        color: Theme.bgMain
        z: -100
    }

    StatusBar {
        anchors.top: parent.top
        anchors.left: parent.left
    }

    SplMeterWidget {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 20
        anchors.rightMargin: 20
        z: 100
    }

    // --- Conteneur Central (Sécurité et Informations) ---
    Item {
        id: centerGroup
        anchors.centerIn: root
        width: parent.width * 0.5
        height: 630
        anchors.verticalCenterOffset: -30
        z: -1

        CenterHub {
            anchors.centerIn: parent
            width: parent.width; height: parent.height
        }

        Image {
            id: renaultLogo
            source: "../assets/Renault-Logo-w.png"
            anchors.centerIn: parent
            fillMode: Image.PreserveAspectFit
            width: parent.width * 0.25
        }

        CarStatusWidget {
            anchors.centerIn: parent
        }
    }

    // ==========================================
    // NOUVEAU : PANNEAU DE FIN DE SESSION
    // ==========================================
    Rectangle {
        id: sessionOverlay
        anchors.centerIn: parent
        width: 700
        height: 450
        color: Qt.rgba(0, 0, 0, 0.7) // Fond semi-transparent
        radius: 20
        border.color: Qt.rgba(1, 1, 1, 0.1)
        border.width: 2

        // État de base (caché et réduit pour l'effet de pop-in)
        opacity: 0.0
        scale: 0.8
        z: 50

        Column {
            anchors.centerIn: parent
            spacing: 30
            width: parent.width * 0.8

            Text {
                text: "Trajet en Pause"
                color: "white"
                font.pixelSize: 36
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // Résumé en temps réel du trajet
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 50

                Column {
                    spacing: 5
                    Text { text: "Distance"; color: Theme.unselected; font.pixelSize: 16; anchors.horizontalCenter: parent.horizontalCenter }
                    Text {
                        text: bridge.stats !== undefined && bridge.stats.distance_km !== undefined ? bridge.stats.distance_km.toFixed(1) + " km" : "0.0 km"
                        color: Theme.main; font.pixelSize: 28; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
                Column {
                    spacing: 5
                    Text { text: "Consommation"; color: Theme.unselected; font.pixelSize: 16; anchors.horizontalCenter: parent.horizontalCenter }
                    Text {
                        text: bridge.stats !== undefined && bridge.stats.session_fuel_l !== undefined ? bridge.stats.session_fuel_l.toFixed(1) + " L" : "0.0 L"
                        color: Theme.main; font.pixelSize: 28; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
                Column {
                    spacing: 5
                    Text { text: "Coût estimé"; color: Theme.unselected; font.pixelSize: 16; anchors.horizontalCenter: parent.horizontalCenter }
                    Text {
                        text: bridge.stats !== undefined && bridge.stats.session_cost !== undefined ? bridge.stats.session_cost.toFixed(2) + " €" : "0.00 €"
                        color: Theme.main; font.pixelSize: 28; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }

            Item { width: 1; height: 20 } // Espaceur

            // Boutons d'action
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 30

                // Bouton Reprendre
                Rectangle {
                    width: 220; height: 60; radius: 10
                    color: Qt.rgba(1, 1, 1, 0.1)
                    border.color: Qt.rgba(1, 1, 1, 0.3); border.width: 2

                    Text { anchors.centerIn: parent; text: "Continuer"; color: "white"; font.pixelSize: 20; font.bold: true }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: bridge.resumeTripSession() // Appel Python
                        onPressed: parent.opacity = 0.5
                        onReleased: parent.opacity = 1.0
                    }
                }

                // Bouton Terminer
                Rectangle {
                    width: 280; height: 60; radius: 10
                    color: Theme.main // Couleur principale de ton thème

                    Text { anchors.centerIn: parent; text: "Terminer & Sauvegarder"; color: "white"; font.pixelSize: 20; font.bold: true }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: bridge.endTripSession() // Appel Python
                        onPressed: parent.opacity = 0.7
                        onReleased: parent.opacity = 1.0
                    }
                }
            }
        }
    }

    // ==========================================
    // INSTRUMENTATION GAUCHE
    // ==========================================
    Item {
        id: leftGauges
        width: 500; height: 450
        anchors.verticalCenter: root.verticalCenter; anchors.verticalCenterOffset: 50
        anchors.left: root.left; anchors.leftMargin: root.width * -0.015

        SpeedometerBmw {
            id: speedo
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left
            scale: 1.15
        }

        BigFuelGauge {
            id: bigFuel
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: 600
            anchors.left: parent.left
        }
    }

    // ==========================================
    // INSTRUMENTATION DROITE
    // ==========================================
    Item {
        id: rightGauges
        width: 500; height: 400
        anchors.verticalCenter: root.verticalCenter; anchors.verticalCenterOffset: 50
        anchors.right: root.right; anchors.rightMargin: root.width * -0.015

        TachometerBmw {
            id: tacho
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
            scale: 1.15
        }

        BigTempGauge {
            id: bigTemp
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: 600
            anchors.right: parent.right
        }
    }

    // ==========================================
    // BANDEAU D'INFORMATIONS INFÉRIEUR
    // ==========================================
    Item {
        id: bottomBar
        anchors.bottom: parent.bottom; anchors.bottomMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.9; height: 40

        // ... (J'ai conservé toute ta logique de bottomBar intacte ici)
        property real autonomy: bridge.stats !== undefined && bridge.stats.autonomy !== undefined ? bridge.stats.autonomy : 450
        property real outsideTemp: bridge.data !== undefined && bridge.data.outside_temp !== undefined ? bridge.data.outside_temp : 21.5
        property string timeString: Qt.formatTime(new Date(), "hh:mm")

        Timer { interval: 1000; running: true; repeat: true; onTriggered: bottomBar.timeString = Qt.formatTime(new Date(), "hh:mm") }

        property int currentScreenIndex: 0
        property bool isInitialized: false
        property bool serviceWarning: bridge.data !== undefined && bridge.data.service_warning !== undefined ? bridge.data.service_warning : false
        property bool comodoUp: bridge.data !== undefined && bridge.data.comodo_up !== undefined ? bridge.data.comodo_up : false
        property bool comodoDown: bridge.data !== undefined && bridge.data.comodo_down !== undefined ? bridge.data.comodo_down : false

        onServiceWarningChanged: { if (!bottomBar.isInitialized && bottomBar.serviceWarning === true) { bottomBar.currentScreenIndex = 2; bottomBar.isInitialized = true } }
        onComodoUpChanged: { if (bottomBar.comodoUp === true) { bottomBar.currentScreenIndex = (bottomBar.currentScreenIndex + 1) % 3 } }
        onComodoDownChanged: { if (bottomBar.comodoDown === true) { bottomBar.currentScreenIndex = (bottomBar.currentScreenIndex - 1 + 3) % 3 } }

        Text {
            id: autonomyText
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            text: "→ " + bottomBar.autonomy.toFixed(0) + " km"
            color: Theme.textMain; font.pixelSize: 24; font.family: "Arial"; opacity: 0.8
        }

        Text {
            id: avgB
            anchors.left : autonomyText.right; anchors.leftMargin: 40; anchors.verticalCenter: parent.verticalCenter
            text: bridge.stats !== undefined && bridge.stats.avg_cons_b !== undefined ? "Avg " + bridge.stats.avg_cons_b.toFixed(1) : "0.0"
            color: Theme.textMain; font.pixelSize: 24; font.family: "Arial"; opacity: 0.8
        }

        Item {
            anchors.left: avgB.right; anchors.leftMargin: 40; anchors.verticalCenter: parent.verticalCenter; height: parent.height
            Row {
                visible: bottomBar.currentScreenIndex === 0; anchors.verticalCenter: parent.verticalCenter; spacing: 40
                Text { text: bridge.stats !== undefined && bridge.stats.trip_b !== undefined ? "B : " + bridge.stats.trip_b.toFixed(1) + " km" : "Trip B 0.0 km"; color: Theme.textMain; font.pixelSize: 22; font.family: "Arial"; opacity: 0.8 }
            }
            Row {
                visible: bottomBar.currentScreenIndex === 1; anchors.verticalCenter: parent.verticalCenter
                Text { text: bridge.stats !== undefined && bridge.stats.trip_a !== undefined ? "A : " + bridge.stats.trip_a.toFixed(1) + " km" : "Trip A 0.0 km"; color: Theme.textMain; font.pixelSize: 22; font.family: "Arial"; opacity: 0.8 }
            }
            Row {
                visible: bottomBar.currentScreenIndex === 2; anchors.verticalCenter: parent.verticalCenter
                Text { text: bridge.stats !== undefined && bridge.stats.km_before_service !== undefined ? "Service dans : " + bridge.stats.km_before_service.toFixed(0) + " km" : "Service : ---"; color: (bridge.data !== undefined && bridge.data.service_warning === true) ? Theme.danger : Theme.textMain; font.pixelSize: 22; font.bold: (bridge.data !== undefined && bridge.data.service_warning === true); font.family: "Arial"; opacity: 0.9 }
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; anchors.horizontalCenterOffset: 95; spacing: 60
            Text { text: bottomBar.timeString; color: Theme.textMain; font.pixelSize: 24; font.family: "Arial"; opacity: 0.9 }
            Text { text: bridge.data !== undefined && bridge.data.odometer !== undefined ? bridge.data.odometer.toFixed(0) + " km" : "0 km"; color: Theme.textMain; font.pixelSize: 24; font.family: "Arial"; opacity: 0.9 }
        }

        Text {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            text: bottomBar.outsideTemp.toFixed(1) + " °C"; color: Theme.textMain; font.pixelSize: 24; font.family: "Arial"; opacity: 0.8
        }
    }

    // ==========================================
    // MOTEUR D'ANIMATION (ÉTATS)
    // ==========================================
    states: [
        State {
            name: "PAUSED"
            // Se déclenche quand la clé est coupée mais encore sur le contact
            when: root.sessionState === "PAUSED"

            // 1. Les compteurs sortent complètement de l'écran (-800px)
            PropertyChanges { target: speedo; anchors.leftMargin: -800; opacity: 0.0 }
            PropertyChanges { target: tacho; anchors.rightMargin: -800; opacity: 0.0 }
            PropertyChanges { target: bigFuel; anchors.leftMargin: -800; opacity: 0.0 }
            PropertyChanges { target: bigTemp; anchors.rightMargin: -800; opacity: 0.0 }

            // 2. On cache le logo central de la voiture pour faire de la place
            PropertyChanges { target: centerGroup; opacity: 0.0; scale: 0.8 }

            // 3. On affiche le grand panneau de résumé
            PropertyChanges { target: sessionOverlay; opacity: 1.0; scale: 1.0 }
        },
        State {
            name: "DRIVE"
            // État par défaut (RUNNING ou IDLE)
            when: root.sessionState == "RUNNING"

            // On remet tout en place (position 0)
            PropertyChanges { target: speedo; anchors.leftMargin: 0; opacity: 1.0 }
            PropertyChanges { target: tacho; anchors.rightMargin: 0; opacity: 1.0 }
            PropertyChanges { target: bigFuel; anchors.leftMargin: -600; opacity: 0.0 }
            PropertyChanges { target: bigTemp; anchors.rightMargin: -600; opacity: 0.0 }

            PropertyChanges { target: centerGroup; opacity: 1.0; scale: 1.0 }
            PropertyChanges { target: sessionOverlay; opacity: 0.0; scale: 0.8 }
        }
    ]

    transitions: [
        Transition {
            // S'applique à l'opacité, l'échelle (scale) et les marges
            NumberAnimation {
                properties: "opacity, anchors.leftMargin, anchors.rightMargin, scale"
                duration: 700
                easing.type: Easing.InOutCubic
            }
        }
    ]
}