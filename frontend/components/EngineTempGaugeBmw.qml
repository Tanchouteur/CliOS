import QtQuick
import "../style"
Item {
    id: gaugeRoot

    // --- Propriétés Publiques ---
    property real p0X: 0
    property real p0Y: 0
    property real vanishingPointX: 0
    property real vanishingPointY: 0

    property real engineTemp: bridge.data.engine_temp !== undefined ? bridge.data.engine_temp : 90.0
    property real smoothTemp: engineTemp
    Behavior on smoothTemp { SpringAnimation { spring: 10.0; damping: 0.8 } }

    property real minTemp: 50.0
    property real maxTemp: 130.0
    property int intervalG: 40 // Pour avoir les traits 50, 90, 130

    // --- Géométrie Interne ---
    // Pas de miroir ici, on prend directement les coordonnées du Tacho
    property int startXG: gaugeRoot.p0X - 15
    property int endXG: gaugeRoot.p0X - 190
    property int yPos: gaugeRoot.p0Y - 5

    // Chemin de base pour le rail
    Path {
        id: tempPath
        startX: gaugeRoot.startXG; startY: gaugeRoot.yPos;
        PathLine { x: gaugeRoot.endXG; y: gaugeRoot.yPos }
    }

    // --- Jauge Dynamique ---
    Repeater {
        model: 100
        Item {
            id: tempDelegate
            z: 5

            property real myProgress: index / 100.0
            property real segmentVal: gaugeRoot.minTemp + (myProgress * (gaugeRoot.maxTemp - gaugeRoot.minTemp))

            // Visibilité : Se remplit jusqu'à la température actuelle
            visible: segmentVal <= Math.max(gaugeRoot.smoothTemp, gaugeRoot.minTemp)

            property color fillColor: {
                if (segmentVal >= 100.0) return Theme.mainDark
                if (segmentVal <= 70.0) return Theme.secondary
                return "#d1caca"
            }

            PathInterpolator {
                id: tempRail;
                progress: tempDelegate.myProgress;
                path: tempPath
            }

            Rectangle {
                width: 22
                height: 3
                x: tempRail.x - 3
                y: tempRail.y - (height / 2)
                transformOrigin: Item.Left

                // Transformation de perspective
                property real deltaY: gaugeRoot.vanishingPointY - tempRail.y
                property real deltaX: gaugeRoot.vanishingPointX - tempRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.05; color: "#FFFFFF" }
                    GradientStop { position: 0.06; color: tempDelegate.fillColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }
    }

    // --- Graduations et Étiquettes ---
    Repeater {
        model: Math.round((gaugeRoot.maxTemp - gaugeRoot.minTemp) / gaugeRoot.intervalG) + 1

        Item {
            id: tickTempDelegate
            z: 10


            property int tickVal: gaugeRoot.minTemp + (index * gaugeRoot.intervalG)
            property real myProgress: (tickVal - gaugeRoot.minTemp) / (gaugeRoot.maxTemp - gaugeRoot.minTemp)

            PathInterpolator {
                id: tickTempRail
                progress: tickTempDelegate.myProgress
                path: tempPath
            }

            Rectangle {
                width: 15
                height: 2
                x: tickTempRail.x
                y: tickTempRail.y - (height / 2) + 4
                transformOrigin: Item.Left

                property real deltaY: gaugeRoot.vanishingPointY - tickTempRail.y
                property real deltaX: gaugeRoot.vanishingPointX - tickTempRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.1; color: "#FFFFFF" }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Text {
                text: tickTempDelegate.tickVal

                visible: index !== 0

                color: Theme.textDimmed
                font.pixelSize: 18
                font.bold: true
                font.family: "Arial"
                x: tickTempRail.x - (width / 2)
                y: tickTempRail.y - 34
            }
        }
    }

    // --- Affichage Numérique ---
    Column {
        x: gaugeRoot.endXG - 45
        y: gaugeRoot.yPos - 30
        spacing: 0

        Text {
            text: Math.min(Math.max(gaugeRoot.smoothTemp, gaugeRoot.minTemp), 150.0).toFixed(0)
            color: Theme.textMain
            font.pixelSize: 18
            font.bold: true
            font.family: "Arial"
            opacity: 0.9
        }

        Text {
            text: "°C"
            color: Theme.textDimmed
            font.pixelSize: 10
            font.family: "Arial"
        }
    }
}