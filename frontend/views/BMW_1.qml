import QtQuick
import QtQuick.Shapes
import "../components"
import "../.."

Item {
    id: root

    // --- Palette de Couleurs Globale ---
    readonly property color bgNoir: "#090909"
    readonly property color texteBlanc: "#f3f3f3"

    readonly property color voyantVert: "#2ecc71"
    readonly property color voyantRouge: "#e74c3c"
    readonly property color voyantBleu: "#3498db"
    readonly property color voyantOrange: "#e67e22"

    // --- Arrière-plan Principal ---
    Rectangle {
        anchors.fill: parent
        color: root.bgNoir
        z: -100 // Maintien en arrière-plan absolu
    }

    // --- Conteneur Central (Sécurité et Informations) ---
    Item {
        id: centerGroup
        anchors.centerIn: root
        width: parent.width * 0.4
        height: 400
        z: -1

        // Filigrane constructeur
        Image {
            id: renaultLogo
            source: "../assets/Renault-Logo-w.png"
            anchors.centerIn: parent
            fillMode: Image.PreserveAspectFit
            opacity: 0.1
            width: parent.width * 0.25
        }

        // --- Fenêtre d'État du Véhicule ---
        Item {
            id: carStatusPopup
            anchors.centerIn: parent
            width: 100
            height: 200
            scale: 1.4

            // Paramètres d'état des ouvrants et de sécurité
            property bool doorFLOpen: bridge.data.door_fl_open !== undefined ? bridge.data.door_fl_open : false
            property bool doorFROpen: bridge.data.door_fr_open !== undefined ? bridge.data.door_fr_open : false
            property bool doorRLOpen: bridge.data.door_rl_open !== undefined ? bridge.data.door_rl_open : false
            property bool doorRROpen: bridge.data.door_rr_open !== undefined ? bridge.data.door_rr_open : false
            property bool trunkOpen: bridge.data.trunk_open !== undefined ? bridge.data.trunk_open : false
            property bool seatbelt: bridge.data.driver_unbelted !== undefined ? bridge.data.driver_unbelted : false

            // Logique d'affichage contextuel (visible si une anomalie est détectée)
            property bool isAnyDoorOpen: doorFLOpen || doorFROpen || doorRLOpen || doorRROpen || trunkOpen || seatbelt
            opacity: isAnyDoorOpen ? 1.0 : 0.0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 300 } }

            // Châssis de représentation
            Rectangle {
                id: carBody
                width: 60
                height: 140
                anchors.centerIn: parent
                color: "#333333"
                radius: 15
                border.color: "#555555"
                border.width: 2

                Rectangle {
                    width: parent.width - 10; height: 20
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top; anchors.topMargin: 25
                    color: "#111111"; radius: 5
                }

                Rectangle {
                    width: parent.width - 15; height: 15
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 15
                    color: "#111111"; radius: 5
                }
            }

            // Composants dynamiques pour les ouvrants
            component CarDoor: Rectangle {
                property bool isOpen: false
                property real openAngle: 45

                width: 6; height: 35
                color: isOpen ? "#ff0033" : "#333333"
                border.color: isOpen ? "#ff0033" : "#555555"

                rotation: isOpen ? openAngle : 0
                Behavior on rotation { SpringAnimation { spring: 5.0; damping: 0.7 } }
                Behavior on color { ColorAnimation { duration: 200 } }
            }

            component CarHoodTrunk: Rectangle {
                property bool isOpen: false
                property real openYOffset: -10

                width: 40; height: 10
                anchors.horizontalCenter: parent.horizontalCenter
                color: isOpen ? "#ff0033" : "#333333"
                border.color: isOpen ? "#ff0033" : "#555555"
                radius: 3

                transform: Translate { y: isOpen ? openYOffset : 0 }
                Behavior on transform { SpringAnimation { spring: 5.0; damping: 0.7 } }
                Behavior on color { ColorAnimation { duration: 200 } }
            }

            // Instanciation des portes
            CarDoor {
                x: carBody.x - width + 1; y: carBody.y + 35
                transformOrigin: Item.TopRight
                openAngle: 60
                isOpen: parent.doorFLOpen
            }

            CarDoor {
                x: carBody.x + carBody.width - 1; y: carBody.y + 35
                transformOrigin: Item.TopLeft
                openAngle: -60
                isOpen: parent.doorFROpen
            }

            CarDoor {
                x: carBody.x - width + 1; y: carBody.y + 75
                height: 30
                transformOrigin: Item.TopRight
                openAngle: 60
                isOpen: parent.doorRLOpen
            }

            CarDoor {
                x: carBody.x + carBody.width - 1; y: carBody.y + 75
                height: 30
                transformOrigin: Item.TopLeft
                openAngle: -60
                isOpen: parent.doorRROpen
            }

            // Instanciation du coffre
            CarHoodTrunk {
                y: carBody.y + carBody.height - height - 5
                openYOffset: 15
                isOpen: parent.trunkOpen
            }

            // Indicateur de ceinture de sécurité
            VoyantIcon {
                width: 30; height: 30
                anchors.top: parent.top
                anchors.topMargin: 80
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: -15

                isActive: parent.seatbelt === true
                activeColor: root.voyantRouge
                inactiveColor: root.bgNoir

                iconSource: "../assets/icons/seatbelt.svg"
                label: "C"
            }
        }

        // Indicateur de désactivation de l'airbag passager
        VoyantIcon {
            width: 50; height: 50
            anchors.top: parent.top
            anchors.topMargin: 15
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.horizontalCenterOffset: 0

            isActive: bridge.data.passenger_disabled === true
            activeColor: root.voyantOrange
            inactiveColor: root.bgNoir

            iconSource: "../assets/icons/airbag.svg"
            label: "BAG\nOFF"
        }

        // Indicateur de frein de stationnement
        VoyantIcon {
            id: handbrakeVoyant
            width: 45; height: 45
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 30
            anchors.horizontalCenter: parent.horizontalCenter

            isActive: bridge.data.handbrake === true
            activeColor: root.voyantRouge
            iconSource: "../assets/icons/handbrake.svg"
            label: "(P)"
        }
    }

    // --- Instrumentation Principale ---

    // Compteur de vitesse (Gauche)
    SpeedometerBmw {
        id: speedo
        anchors.verticalCenter: root.verticalCenter
        anchors.left: root.left
        anchors.leftMargin: root.width * 0.04

        // Indicateur de direction gauche
        VoyantIcon {
            id: turnLeftLight
            anchors.verticalCenter: parent.verticalCenter
            anchors.topMargin: 40
            anchors.right: speedo.right
            anchors.rightMargin: -20
            width: 50
            height: 50

            isActive: bridge.data.turn_left !== undefined ? bridge.data.turn_left : false
            activeColor: root.voyantVert

            iconSource: "../assets/icons/turn_left.svg"
            label: "⬅️"
        }

        // Bloc central d'indicateurs d'éclairage
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenterOffset: 170
            anchors.verticalCenterOffset: 10
            spacing: 6

            VoyantIcon {
                width: 40; height: 40
                isActive: bridge.data.fog_front === true
                iconSource: "../assets/icons/fog_front.svg"
                activeColor: root.voyantVert; label: "AV"
            }

            VoyantTriStateIcon {
                width: 55; height: 55
                isPos1: bridge.data.low_beam === true
                isPos2: bridge.data.high_beam === true

                iconPos1: "../assets/icons/low_beam.svg"
                iconPos2: "../assets/icons/high_beam.svg"
                iconOff: "../assets/icons/low_beam.svg"

                colorPos1: root.voyantVert
                colorPos2: root.voyantBleu
                colorOff: "#333333"
            }

            VoyantIcon {
                width: 40; height: 40
                isActive: bridge.data.fog_rear === true
                activeColor: root.voyantOrange
                label: "AR"
                iconSource: "../assets/icons/fog_rear.svg"
            }
        }
    }

    // Compte-tours (Droite)
    TachometerBmw {
        id: tacho
        anchors.verticalCenter: root.verticalCenter
        anchors.right: root.right
        anchors.rightMargin: root.width * 0.04

        // Indicateur de direction droit
        VoyantIcon {
            id: turnRightLight
            anchors.verticalCenter: parent.verticalCenter
            anchors.topMargin: 40
            anchors.left: tacho.left
            anchors.leftMargin: -20
            width: 50
            height: 50

            isActive: bridge.data.turn_right !== undefined ? bridge.data.turn_right : false
            activeColor: root.voyantVert

            iconSource: "../assets/icons/turn_right.svg"
            label: "➡️"
        }

        // Bloc central d'indicateurs moteur
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenterOffset: -122
            anchors.verticalCenterOffset: 0
            spacing: -10

            VoyantTriStateIcon {
                width: 55; height: 55

                isPos1: bridge.data.engine_light === "ORANGE"
                isPos2: bridge.data.engine_light === "RED"

                iconPos1: "../assets/icons/engine.svg"
                iconPos2: "../assets/icons/engine.svg"
                iconOff:  "../assets/icons/engine.svg"

                colorPos1: root.voyantOrange
                colorPos2: root.voyantRouge
                colorOff: "#171717"
            }

            VoyantIcon {
                property bool glowPlugPreheat: bridge.data.glow_plug_status === undefined ? false : bridge.data.glow_plug_status.toFixed(0) >= 100
                width: 55; height: 55;

                isActive: glowPlugPreheat === true;
                inactiveColor: "#171717"
                activeColor: root.voyantOrange
                label: "PRE"
                iconSource: "../assets/icons/coil.svg"
            }
        }
    }

    // --- Instrumentation Secondaire ---

    // Jauge de température de liquide de refroidissement
    EngineTempGaugeBmw {
        id: tempGauge
        scale: 0.8
        anchors.bottom: tacho.bottom
        anchors.right: tacho.right
        anchors.bottomMargin: -20
        anchors.rightMargin: -80
    }

    // Jauge de niveau de carburant
    FuelGaugeBmw {
        id: fuelGauge
        scale: 0.8
        anchors.bottom: speedo.bottom
        anchors.left: speedo.left
        anchors.bottomMargin: -20
        anchors.leftMargin: -80
    }

    // --- Lien Visuel Central ---
    Rectangle {
        z: -2 // Positionnement sous les indicateurs
        anchors.bottom: speedo.bottom
        anchors.bottomMargin: 6
        anchors.left: speedo.right
        anchors.leftMargin: -120
        anchors.right: tacho.left
        anchors.rightMargin: -120
        height: 5

        // Dégradé de transition entre les cadrans principaux
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.05; color: "#A3ffffff" }
            GradientStop { position: 0.95; color: "#A3ffffff" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // --- Bandeau d'Informations Inférieur ---
    Item {
        id: bottomBar
        anchors.top: fuelGauge.bottom
        anchors.topMargin: -15
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.9
        height: 40

        // Variables système
        property real autonomy: bridge.data.autonomy !== undefined ? bridge.data.autonomy : 450
        property real outsideTemp: bridge.data.outside_temp !== undefined ? bridge.data.outside_temp : 21.5
        property string timeString: Qt.formatTime(new Date(), "hh:mm")

        // Horloge système
        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: bottomBar.timeString = Qt.formatTime(new Date(), "hh:mm")
        }

        // --- Gestionnaire d'Affichage Dynamique (Carrousel) ---
        property int currentScreenIndex: 0
        property bool isInitialized: false

        // Liaison des variables de contrôle
        property bool serviceWarning: bridge.data.service_warning !== undefined ? bridge.data.service_warning : false
        property bool comodoUp: bridge.data.comodo_up !== undefined ? bridge.data.comodo_up : false
        property bool comodoDown: bridge.data.comodo_down !== undefined ? bridge.data.comodo_down : false

        // Gestionnaires d'événements
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

        // Bloc Autonomie
        Text {
            id: autonomyText
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "→ " + bottomBar.autonomy.toFixed(0) + " km"
            color: root.texteBlanc
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }

        // Bloc Consommation Moyenne
        Text {
            id: avgB
            anchors.left : autonomyText.right
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter

            text: bridge.data.avg_cons_b !== undefined ? "Avg " + bridge.data.avg_cons_b.toFixed(1) : "0.0"
            color: root.texteBlanc
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }

        // --- Conteneur Dynamique ---
        Item {
            anchors.left: avgB.right
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            height: parent.height

            // Affichage 0 : Distance du trajet B
            Row {
                visible: bottomBar.currentScreenIndex === 0
                anchors.verticalCenter: parent.verticalCenter
                spacing: 40

                Text {
                    text: bridge.data.trip_b !== undefined ? "B : " + bridge.data.trip_b.toFixed(1) + " km" : "Trip B 0.0 km"
                    color: root.texteBlanc
                    font.pixelSize: 22
                    font.family: "Arial"
                    opacity: 0.8
                }
            }

            // Affichage 1 : Distance du trajet A
            Row {
                visible: bottomBar.currentScreenIndex === 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: bridge.data.trip_a !== undefined ? "A : " + bridge.data.trip_a.toFixed(1) + " km" : "Trip A 0.0 km"
                    color: root.texteBlanc
                    font.pixelSize: 22
                    font.family: "Arial"
                    opacity: 0.8
                }
            }

            // Affichage 2 : Indicateur de maintenance
            Row {
                visible: bottomBar.currentScreenIndex === 2
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: bridge.data.km_before_service !== undefined ? "Service dans : " + bridge.data.km_before_service.toFixed(0) + " km" : "Service : ---"
                    color: (bridge.data.service_warning === true) ? root.voyantRouge : root.texteBlanc
                    font.pixelSize: 22
                    font.bold: (bridge.data.service_warning === true)
                    font.family: "Arial"
                    opacity: 0.9
                }
            }
        }

        // --- Bloc Central (Horloge et Odomètre) ---
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenterOffset: 95
            spacing: 60

            Text {
                text: bottomBar.timeString
                color: root.texteBlanc
                font.pixelSize: 24
                font.family: "Arial"
                opacity: 0.9
            }

            Text {
                text: bridge.data.odometer !== undefined ? bridge.data.odometer.toFixed(0) + " km" : "0 km"
                color: root.texteBlanc
                font.pixelSize: 24
                font.family: "Arial"
                opacity: 0.9
            }
        }

        // --- Bloc Droit (Température Extérieure) ---
        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: bottomBar.outsideTemp.toFixed(1) + " °C"
            color: root.texteBlanc
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }
    }
}