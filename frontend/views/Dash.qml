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

    Rectangle {
        anchors.fill: parent
        color: root.bgNoir
        z: -100
    }

    // --- Conteneur Central (Sécurité et Informations) ---
    Item {
        id: centerGroup
        anchors.centerIn: root
        width: parent.width * 0.4
        height: 400
        z: -1

        Image {
            id: renaultLogo
            source: "../assets/Renault-Logo-w.png"
            anchors.centerIn: parent
            fillMode: Image.PreserveAspectFit
            opacity: 0.1
            width: parent.width * 0.25
        }

        // ==========================================
        // APPEL DU NOUVEAU COMPOSANT ICI
        // ==========================================
        CarStatusWidget {
            anchors.centerIn: parent
            scale: 1.4
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
    SpeedometerBmw {
        id: speedo
        anchors.verticalCenter: root.verticalCenter
        anchors.left: root.left
        anchors.leftMargin: root.width * -0.03
    }

    TachometerBmw {
        id: tacho
        anchors.verticalCenter: root.verticalCenter
        anchors.right: root.right
        anchors.rightMargin: root.width * -0.03
    }

    // --- Lien Visuel Central ---
    Rectangle {
        z: -2
        anchors.bottom: speedo.bottom
        anchors.bottomMargin: 6
        anchors.left: speedo.right
        anchors.leftMargin: -120
        anchors.right: tacho.left
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

    // --- Bandeau d'Informations Inférieur ---
    Item {
        id: bottomBar
        anchors.top: speedo.bottom
        anchors.topMargin: 0
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.9
        height: 40

        property real autonomy: bridge.data.autonomy !== undefined ? bridge.data.autonomy : 450
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
            color: root.texteBlanc
            font.pixelSize: 24
            font.family: "Arial"
            opacity: 0.8
        }

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
                    text: bridge.data.trip_b !== undefined ? "B : " + bridge.data.trip_b.toFixed(1) + " km" : "Trip B 0.0 km"
                    color: root.texteBlanc
                    font.pixelSize: 22
                    font.family: "Arial"
                    opacity: 0.8
                }
            }

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