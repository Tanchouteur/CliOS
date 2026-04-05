import QtQuick
import QtQuick.Shapes
import "../components"
import "../style"

Item {
    id: root

    // Variable qui contrôle l'état de l'interface (Vrai = Arrêt, Faux = Conduite)
    property bool isParked: false

    Rectangle {
        anchors.fill: parent
        color: Theme.bgMain
        z: -100
    }

    // --- Conteneur Central (Sécurité et Informations) ---
    Item {
        id: centerGroup
        anchors.centerIn: root
        width: parent.width * 0.5
        height: 600
        anchors.verticalCenterOffset: -40

        z: -1

        CenterHub{
            anchors.centerIn: parent
            width: parent.width; height: parent.height
        }

        Image {
            id: renaultLogo
            source: "../assets/Renault-Logo-w.png"
            anchors.centerIn: parent
            fillMode: Image.PreserveAspectFit
            opacity: 0.1
            width: parent.width * 0.25
        }

        CarStatusWidget {
            anchors.centerIn: parent
            scale: 1.4
        }
    }

    // ==========================================
    // INSTRUMENTATION GAUCHE (Vitesse / Essence)
    // ==========================================
    Item {
        id: leftGauges
        width: 500
        height: 400
        anchors.verticalCenter: root.verticalCenter
        anchors.verticalCenterOffset: 50
        anchors.left: root.left
        anchors.leftMargin: root.width * -0.03

        SpeedometerBmw {
            id: speedo
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: 0 // Position de base
            anchors.left: parent.left
        }

        BigFuelGauge {
            id: bigFuel
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: 600 // Caché en bas par défaut
            anchors.left: parent.left
        }
    }

    // ==========================================
    // INSTRUMENTATION DROITE (Tours / Température)
    // ==========================================
    Item {
        id: rightGauges
        width: 500
        height: 400
        anchors.verticalCenter: root.verticalCenter
        anchors.verticalCenterOffset: 50
        anchors.right: root.right
        anchors.rightMargin: root.width * -0.03

        TachometerBmw {
            id: tacho
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: 0
            anchors.right: parent.right
        }

        BigTempGauge {
            id: bigTemp
            width: 500; height: 400
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: 600 // Caché en bas par défaut
            anchors.right: parent.right
        }
    }

    // --- Lien Visuel Central ---
    Rectangle {
        id: centerLink
        z: -2
        anchors.bottom: leftGauges.bottom
        anchors.bottomMargin: 6
        anchors.left: leftGauges.right
        anchors.leftMargin: -120
        anchors.right: rightGauges.left
        anchors.rightMargin: -120
        height: 5

        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.05; color: "#A3ffffff" }
            GradientStop { position: 0.95; color: "#A3ffffff" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // ==========================================
    // BANDEAU D'INFORMATIONS INFÉRIEUR
    // ==========================================
    Item {
        id: bottomBar

        // MODIFICATION : Ancrage absolu en bas de l'écran
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.9
        height: 40

        property real autonomy: bridge.stats.autonomy !== undefined ? bridge.stats.autonomy : 450
        property real outsideTemp: bridge.data.outside_temp !== undefined ? bridge.data.outside_temp : 21.5
        property string timeString: Qt.formatTime(new Date(), "hh:mm")

        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: bottomBar.timeString = Qt.formatTime(new Date(), "hh:mm")
        }

        property int currentScreenIndex: 0
        property bool isInitialized: false

        property bool serviceWarning: bridge.data.service_warning !== undefined ? bridge.data.service_warning : false
        property bool comodoUp: bridge.data.comodo_up !== undefined ? bridge.data.comodo_up : false
        property bool comodoDown: bridge.data.comodo_down !== undefined ? bridge.data.comodo_down : false

        onServiceWarningChanged: {
            if (!bottomBar.isInitialized && bottomBar.serviceWarning === true) {
                bottomBar.currentScreenIndex = 2
                bottomBar.isInitialized = true
            }
        }

        onComodoUpChanged: {
            if (bottomBar.comodoUp === true) {
                bottomBar.currentScreenIndex = (bottomBar.currentScreenIndex + 1) % 3
            }
        }

        onComodoDownChanged: {
            if (bottomBar.comodoDown === true) {
                bottomBar.currentScreenIndex = (bottomBar.currentScreenIndex - 1 + 3) % 3
            }
        }

        Text {
            id: autonomyText
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "→ " + bottomBar.autonomy.toFixed(0) + " km"
            color: Theme.textMain
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }

        Text {
            id: avgB
            anchors.left : autonomyText.right
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            text: bridge.stats.avg_cons_b !== undefined ? "Avg " + bridge.stats.avg_cons_b.toFixed(1) : "0.0"
            color: Theme.textMain
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }

        Item {
            anchors.left: avgB.right
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            height: parent.height

            Row {
                visible: bottomBar.currentScreenIndex === 0
                anchors.verticalCenter: parent.verticalCenter
                spacing: 40
                Text {
                    text: bridge.stats.trip_b !== undefined ? "B : " + bridge.stats.trip_b.toFixed(1) + " km" : "Trip B 0.0 km"
                    color: Theme.textMain
                    font.pixelSize: 22
                    font.family: "Arial"
                    opacity: 0.8
                }
            }

            Row {
                visible: bottomBar.currentScreenIndex === 1
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    text: bridge.stats.trip_a !== undefined ? "A : " + bridge.stats.trip_a.toFixed(1) + " km" : "Trip A 0.0 km"
                    color: Theme.textMain
                    font.pixelSize: 22
                    font.family: "Arial"
                    opacity: 0.8
                }
            }

            Row {
                visible: bottomBar.currentScreenIndex === 2
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    text: bridge.stats.km_before_service !== undefined ? "Service dans : " + bridge.stats.km_before_service.toFixed(0) + " km" : "Service : ---"
                    color: (bridge.stats.service_warning === true) ? Theme.danger : Theme.textMain
                    font.pixelSize: 22
                    font.bold: (bridge.data.service_warning === true)
                    font.family: "Arial"
                    opacity: 0.9
                }
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenterOffset: 95
            spacing: 60

            Text {
                text: bottomBar.timeString
                color: Theme.textMain
                font.pixelSize: 24
                font.family: "Arial"
                opacity: 0.9
            }

            Text {
                text: bridge.data.odometer !== undefined ? bridge.data.odometer.toFixed(0) + " km" : "0 km"
                color: Theme.textMain
                font.pixelSize: 24
                font.family: "Arial"
                opacity: 0.9
            }
        }

        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: bottomBar.outsideTemp.toFixed(1) + " °C"
            color: Theme.textMain
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }
    }

    // ==========================================
    // MOTEUR D'ANIMATION (GLISSEMENT HORIZONTAL)
    // ==========================================
    states: [
        State {
            name: "PARK"
            when: root.isParked

            // Les compteurs principaux sortent complètement (-600px) et s'effacent
            PropertyChanges { target: speedo; anchors.leftMargin: -600; opacity: 0.0 }
            PropertyChanges { target: tacho; anchors.rightMargin: -600; opacity: 0.0 }

            // Les jauges géantes rentrent, on les laisse à -100px pour dégager un grand espace central
            PropertyChanges { target: bigFuel; anchors.leftMargin: -100; opacity: 1.0 }
            PropertyChanges { target: bigTemp; anchors.rightMargin: -100; opacity: 1.0 }

            PropertyChanges { target: bottomBar; anchors.topMargin: 30 }
            PropertyChanges { target: centerLink; anchors.topMargin: 60; opacity: 0.0 }
        },
        State {
            name: "DRIVE"
            when: !root.isParked

            // Les compteurs principaux reviennent à leur position d'origine (0)
            PropertyChanges { target: speedo; anchors.leftMargin: 0; opacity: 1.0 }
            PropertyChanges { target: tacho; anchors.rightMargin: 0; opacity: 1.0 }

            // Les jauges géantes sortent de l'écran (-600px)
            PropertyChanges { target: bigFuel; anchors.leftMargin: -600; opacity: 0.0 }
            PropertyChanges { target: bigTemp; anchors.rightMargin: -600; opacity: 0.0 }

            PropertyChanges { target: bottomBar; anchors.topMargin: 0 }
            PropertyChanges { target: centerLink; anchors.topMargin: 0; opacity: 1.0 }
        }
    ]

    transitions: [
        Transition {
            // Easing.InOutCubic donne un effet d'accélération/décélération très naturel
            NumberAnimation {
                properties: "opacity, anchors.leftMargin, anchors.rightMargin, anchors.topMargin, anchors.bottomMargin"
                duration: 700
                easing.type: Easing.InOutCubic
            }
        }
    ]

    // ==========================================
    // BOUTON DE TEST TEMPORAIRE
    // ==========================================
    // APRÈS — zone de test restreinte (ex: coin bas-droit)
    Rectangle {
        width: 60; height: 60
        anchors.bottom: parent.bottom
        anchors.right:  parent.right
        color: Qt.rgba(1, 1, 1, 0.05)
        radius: 8

        MouseArea {
            anchors.fill: parent
            onClicked: root.isParked = !root.isParked
        }
    }
}