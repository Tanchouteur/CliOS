import QtQuick
import "../style"

Item {
    id: widgetRoot

    // Dimensions de base (le scale sera géré par le parent)
    width: 100
    height: 200

    // Paramètres d'état des ouvrants et de sécurité liés au bridge
    property bool doorFLOpen: bridge.data.door_fl_open !== undefined ? bridge.data.door_fl_open : false
    property bool doorFROpen: bridge.data.door_fr_open !== undefined ? bridge.data.door_fr_open : false
    property bool doorRLOpen: bridge.data.door_rl_open !== undefined ? bridge.data.door_rl_open : false
    property bool doorRROpen: bridge.data.door_rr_open !== undefined ? bridge.data.door_rr_open : false
    property bool trunkOpen: bridge.data.trunk_open !== undefined ? bridge.data.trunk_open : false
    property bool seatbelt: bridge.data.driver_unbelted !== undefined ? bridge.data.driver_unbelted : false

    // Logique d'affichage contextuel
    property bool isAnyDoorOpen: doorFLOpen || doorFROpen || doorRLOpen || doorRROpen || trunkOpen || seatbelt

    opacity: isAnyDoorOpen ? 1.0 : 0.0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 300 } }

    // --- Châssis de représentation ---
    Rectangle {
        id: carBody
        width: 60
        height: 140
        anchors.centerIn: parent
        color: "#333333"
        radius: 15
        border.color: "#555555"
        border.width: 2

        // Pare-brise
        Rectangle {
            width: parent.width - 10; height: 20
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 25
            color: "#111111"; radius: 5
        }

        // Lunette arrière
        Rectangle {
            width: parent.width - 15; height: 15
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 15
            color: "#111111"; radius: 5
        }
    }

    // --- Composants dynamiques pour les ouvrants ---
    component CarDoor: Rectangle {
        property bool isOpen: false
        property real openAngle: 45

        width: 6; height: 35
        color: isOpen ? Theme.danger : "#333333"
        border.color: isOpen ? Theme.danger : "#555555"

        rotation: isOpen ? openAngle : 0
        Behavior on rotation { SpringAnimation { spring: 5.0; damping: 0.7 } }
        Behavior on color { ColorAnimation { duration: 200 } }
    }

    component CarHoodTrunk: Rectangle {
        property bool isOpen: false
        property real openYOffset: -10

        width: 40; height: 10
        anchors.horizontalCenter: parent.horizontalCenter
        color: isOpen ? Theme.danger : "#333333"
        border.color: isOpen ? Theme.danger : "#555555"
        radius: 3

        transform: Translate { y: isOpen ? openYOffset : 0 }
        Behavior on transform { SpringAnimation { spring: 5.0; damping: 0.7 } }
        Behavior on color { ColorAnimation { duration: 200 } }
    }

    // --- Instanciation des portes ---
    CarDoor {
        x: carBody.x - width + 1; y: carBody.y + 35
        transformOrigin: Item.TopRight
        openAngle: 60
        isOpen: widgetRoot.doorFLOpen
    }

    CarDoor {
        x: carBody.x + carBody.width - 1; y: carBody.y + 35
        transformOrigin: Item.TopLeft
        openAngle: -60
        isOpen: widgetRoot.doorFROpen
    }

    CarDoor {
        x: carBody.x - width + 1; y: carBody.y + 75
        height: 30
        transformOrigin: Item.TopRight
        openAngle: 60
        isOpen: widgetRoot.doorRLOpen
    }

    CarDoor {
        x: carBody.x + carBody.width - 1; y: carBody.y + 75
        height: 30
        transformOrigin: Item.TopLeft
        openAngle: -60
        isOpen: widgetRoot.doorRROpen
    }

    // --- Instanciation du coffre ---
    CarHoodTrunk {
        y: carBody.y + carBody.height - height - 5
        openYOffset: 15
        isOpen: widgetRoot.trunkOpen
    }

    // --- Indicateur de ceinture de sécurité ---
    VoyantIcon {
        width: 30; height: 30
        anchors.top: parent.top
        anchors.topMargin: 80
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -15

        isActive: widgetRoot.seatbelt === true
        activeColor: Theme.danger // voyantRouge
        inactiveColor: Theme.bgDimmed

        iconSource: "../assets/icons/seatbelt.svg"
        label: "C"
    }
}