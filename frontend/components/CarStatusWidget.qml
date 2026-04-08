import QtQuick
import "../style"

Item {
    id: widgetRoot

    // Dimensions recalculées (100x200 * 1.4)
    width: 140
    height: 280

    property bool doorFLOpen: bridge.data.door_fl_open ?? false
    property bool doorFROpen: bridge.data.door_fr_open ?? false
    property bool doorRLOpen: bridge.data.door_rl_open ?? false
    property bool doorRROpen: bridge.data.door_rr_open ?? false
    property bool trunkOpen: bridge.data.trunk_open ?? false
    property bool seatbelt: bridge.data.driver_unbelted ?? false

    property bool isAnyDoorOpen: doorFLOpen || doorFROpen || doorRLOpen || doorRROpen || trunkOpen || seatbelt

    opacity: isAnyDoorOpen ? 1.0 : 0.0
    visible: opacity > 0

    // OPTIMISATION : enabled: visible coupe les calculs CPU des animations quand c'est caché
    enabled: visible

    Behavior on opacity { NumberAnimation { duration: 300 } }

    // --- Châssis (Dimensions * 1.4) ---
    Rectangle {
        id: carBody
        width: 84  // 60 * 1.4
        height: 196 // 140 * 1.4
        anchors.centerIn: parent
        color: "#333333"
        radius: 21 // 15 * 1.4
        border.color: "#555555"
        border.width: 3 // 2 * 1.4

        // Pare-brise
        Rectangle {
            width: parent.width - 14; height: 28
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 35
            color: "#111111"; radius: 7
        }

        // Lunette arrière
        Rectangle {
            width: parent.width - 21; height: 21
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 21
            color: "#111111"; radius: 7
        }
    }

    // --- Composants dynamiques (Multipliés par 1.4) ---
    component CarDoor: Rectangle {
        property bool isOpen: false
        property real openAngle: 45

        width: 8; height: 49 // 6x35 * 1.4
        color: isOpen ? Theme.danger : "#333333"
        border.color: isOpen ? Theme.danger : "#555555"

        rotation: isOpen ? openAngle : 0
        Behavior on rotation { SpringAnimation { spring: 5.0; damping: 0.7 } }
        Behavior on color { ColorAnimation { duration: 200 } }
    }

    component CarHoodTrunk: Rectangle {
        property bool isOpen: false
        property real openYOffset: -14

        width: 56; height: 14 // 40x10 * 1.4
        anchors.horizontalCenter: parent.horizontalCenter
        color: isOpen ? Theme.danger : "#333333"
        border.color: isOpen ? Theme.danger : "#555555"
        radius: 4

        transform: Translate { y: isOpen ? openYOffset : 0 }
        Behavior on transform { SpringAnimation { spring: 5.0; damping: 0.7 } }
        Behavior on color { ColorAnimation { duration: 200 } }
    }

    // --- Instanciation des portes (Positions recalculées) ---
    CarDoor {
        x: carBody.x - width + 1; y: carBody.y + 49
        transformOrigin: Item.TopRight
        openAngle: 60
        isOpen: widgetRoot.doorFLOpen
    }

    CarDoor {
        x: carBody.x + carBody.width - 1; y: carBody.y + 49
        transformOrigin: Item.TopLeft
        openAngle: -60
        isOpen: widgetRoot.doorFROpen
    }

    CarDoor {
        x: carBody.x - width + 1; y: carBody.y + 105
        height: 42 // 30 * 1.4
        transformOrigin: Item.TopRight
        openAngle: 60
        isOpen: widgetRoot.doorRLOpen
    }

    CarDoor {
        x: carBody.x + carBody.width - 1; y: carBody.y + 105
        height: 42 // 30 * 1.4
        transformOrigin: Item.TopLeft
        openAngle: -60
        isOpen: widgetRoot.doorRROpen
    }

    // --- Instanciation du coffre ---
    CarHoodTrunk {
        y: carBody.y + carBody.height - height - 7
        openYOffset: 21
        isOpen: widgetRoot.trunkOpen
    }

    // --- Indicateur de ceinture ---
    VoyantIcon {
        width: 42; height: 42 // 30 * 1.4
        anchors.top: parent.top
        anchors.topMargin: 112 // 80 * 1.4
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -21

        isActive: widgetRoot.seatbelt
        activeColor: Theme.danger
        inactiveColor: Theme.bgDimmed

        iconSource: "../assets/icons/seatbelt.svg"
        label: "C"
    }
}