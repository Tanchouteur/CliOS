import QtQuick
import "../style"

Item {
    id: root
    width: 500
    height: 400

    // --- Propriétés (Données Véhicule) ---
    property real engineTemp: bridge.data.engine_temp !== undefined ? bridge.data.engine_temp : 90.0
    property real smoothTemp: engineTemp

    property real minTemp: bridge.config.engine_temp.min_display !== undefined ? bridge.config.engine_temp.min_display : 50.0
    property real maxTemp: bridge.config.engine_temp.max_display !== undefined ? bridge.config.engine_temp.max_display : 130.0

    // --- Géométrie et Perspective 3D ---
    property real vanishingPointX: width * 0.25
    property real vanishingPointY: height * 0.50

    property real tubeX: 360
    property real tubeBottomY: 350
    property real tubeTopY: 80

    Path {
        id: tubePath
        startX: root.tubeX; startY: root.tubeBottomY
        PathLine { x: root.tubeX; y: root.tubeTopY }
    }

    // --- Remplissage de l'Éprouvette ---
    Repeater {
        model: 150
        Item {
            id: fillDelegate
            z: 5

            property real myProgress: index / 150.0
            property real segmentVal: root.minTemp + (myProgress * (root.maxTemp - root.minTemp))

            property bool isFilled: segmentVal <= root.smoothTemp
            opacity: isFilled ? 1.0 : 0.15

            // Style BMW : Orange Ambré classique, Rouge vif si surchauffe
            property color fillColor: segmentVal >= 110.0 ? Theme.redLine : Theme.mainLight

            PathInterpolator {
                id: tubeRail
                progress: fillDelegate.myProgress
                path: tubePath
            }

            Rectangle {
                width: 25
                height: 3
                x: tubeRail.x - 10
                y: tubeRail.y - (height / 2)
                transformOrigin: Item.Left

                property real deltaY: root.vanishingPointY - tubeRail.y
                property real deltaX: root.vanishingPointX - tubeRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.1; color: fillDelegate.fillColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }
    }

    // --- Graduations Majeures ---
    Repeater {
        model: 3
        Item {
            id: tickDelegate
            z: 10

            property int tickVal: 50 + (index * 40)
            property real tickProgress: (tickVal - root.minTemp) / (root.maxTemp - root.minTemp)

            PathInterpolator {
                id: tickRail
                progress: tickDelegate.tickProgress
                path: tubePath
            }

            // Trait décalé vers la gauche
            Rectangle {
                width: 15
                height: 2
                x: tickRail.x - width
                y: tickRail.y - (height / 2)
                color: Theme.textDimmed
            }

            // Texte placé à gauche du trait
            Text {
                text: tickDelegate.tickVal
                color: Theme.textDimmed
                font.pixelSize: 16
                font.family: "Arial"
                x: tickRail.x - 50
                y: tickRail.y - 10
            }
        }
    }

    // --- Le Pointeur Dynamique ---
    Item {
        z: 20

        property color pointerColor: root.smoothTemp >= 110.0 ? Theme.redLine : Theme.main

        PathInterpolator {
            id: pointerRail
            progress: Math.min(Math.max((root.smoothTemp - root.minTemp) / (root.maxTemp - root.minTemp), 0.0), 1.0)
            path: tubePath
        }

        x: pointerRail.x
        y: pointerRail.y

        // Barre du curseur pointant vers la gauche
        Rectangle {
            width: 45
            height: 3
            x: -width // Position négative pour aller vers la gauche
            y: -1
            color: parent.pointerColor
        }

        // Texte ancré à l'extrémité gauche de la barre
        Text {
            text: Math.round(root.smoothTemp) + "°"
            color: parent.pointerColor
            font.pixelSize: 38
            font.bold: true
            font.family: "Arial"
            anchors.right: parent.left
            anchors.rightMargin: 55
            anchors.verticalCenter: parent.top

            Behavior on color { ColorAnimation { duration: 300 } }
        }
    }
}