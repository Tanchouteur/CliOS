import QtQuick
import "../style"

Item {
    id: root
    width: 500
    height: 400

    // --- Propriétés (Données Véhicule) ---
    property real fuelLevel: bridge.data.fuel_level !== undefined ? bridge.data.fuel_level : 75.0
    property real smoothFuel: fuelLevel

    property real minFuel: 0.0
    property real maxFuel: 100.0

    // --- Géométrie et Perspective 3D (Corrigée) ---
    property real vanishingPointX: 400 // Point de fuite poussé à fond vers le centre de l'écran (à droite)
    property real vanishingPointY: 200 // Milieu de la hauteur

    // Le tube est maintenant bien collé à gauche (x: 80)
    property real tubeX: 150
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
            property real segmentVal: root.minFuel + (myProgress * (root.maxFuel - root.minFuel))

            property bool isFilled: segmentVal <= root.smoothFuel
            opacity: isFilled ? 1.0 : 0.15

            property color fillColor: segmentVal <= 15.0 ? Theme.redLine : Theme.mainLight

            PathInterpolator {
                id: tubeRail
                progress: fillDelegate.myProgress
                path: tubePath
            }

            Rectangle {
                width: 25
                height: 3
                // On part EXACTEMENT du tube et on s'étend vers la droite
                x: tubeRail.x
                y: tubeRail.y - (height / 2)

                // Le pivot est sur le tube (à gauche du segment)
                transformOrigin: Item.Left

                property real deltaY: root.vanishingPointY - tubeRail.y
                property real deltaX: root.vanishingPointX - tubeRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                // LE SECRET 3D : L'arête blanche (0.0) est sur le tube, et ça fond vers la droite (1.0)
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.1; color: fillDelegate.fillColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }
    }

    // --- Graduations Majeures (0, 1/2, 1) ---
    Repeater {
        model: 3
        Item {
            id: tickDelegate
            z: 10

            property real tickProgress: index / 2.0
            property string tickLabel: index === 0 ? "0" : (index === 1 ? "1/2" : "1")

            PathInterpolator {
                id: tickRail
                progress: tickDelegate.tickProgress
                path: tubePath
            }

            // Trait d'accroche (placé juste à droite du tube)
            Rectangle {
                width: 15
                height: 2
                x: tickRail.x + 5
                y: tickRail.y - (height / 2)
                color: Theme.textDimmed
            }

            // Texte (placé à la suite du trait)
            Text {
                text: tickDelegate.tickLabel
                color: Theme.textDimmed
                font.pixelSize: 16
                font.family: "Arial"
                x: tickRail.x + 25
                y: tickRail.y - 10
            }
        }
    }

    // --- Le Pointeur Dynamique ---
    Item {
        z: 20

        property color pointerColor: root.smoothFuel <= 15.0 ? Theme.redLine : Theme.main

        PathInterpolator {
            id: pointerRail
            progress: Math.min(Math.max((root.smoothFuel - root.minFuel) / (root.maxFuel - root.minFuel), 0.0), 1.0)
            path: tubePath
        }

        x: pointerRail.x
        y: pointerRail.y

        // Barre du curseur pointant vers la droite
        Rectangle {
            width: 45
            height: 3
            x: 0
            y: -1
            color: parent.pointerColor

            layer.enabled: true
            layer.effect: ShaderEffect { }
        }

        // Texte ancré à la pointe droite du curseur
        Text {
            text: Math.round(root.smoothFuel) + " %"
            color: parent.pointerColor
            font.pixelSize: 38
            font.bold: true
            font.family: "Arial"

            anchors.left: parent.left
            anchors.leftMargin: 55
            anchors.verticalCenter: parent.top

            Behavior on color { ColorAnimation { duration: 300 } }
        }
    }
}