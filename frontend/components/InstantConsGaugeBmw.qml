import QtQuick
import "../style"

Item {
    id: gaugeRoot

    // --- Propriétés Publiques ---
    property real referenceWidth: 500
    property real p0X: 0
    property real p0Y: 0
    property real vanishingPointX: 0
    property real vanishingPointY: 0

    property real maxInstCons: 20.0
    property real smoothInstCons: bridge.stats.inst_cons ?? -1.0
    property real avgCons: bridge.stats.avg_cons_b ?? -1.0
    property int intervalG: 5

    // --- Géométrie Interne ---
    // Ajustement des coordonnées pour le rendu visuel en miroir
    property real visualP0X: gaugeRoot.referenceWidth - gaugeRoot.p0X
    property real visualVPX: gaugeRoot.referenceWidth - gaugeRoot.vanishingPointX

    property int startXG: gaugeRoot.visualP0X + 15
    property int endXG: gaugeRoot.visualP0X + 190
    property int yPos: gaugeRoot.p0Y - 5

    // Chemin de base pour le rail de consommation
    Path {
        id: instConsPath
        startX: gaugeRoot.startXG; startY: gaugeRoot.yPos;
        PathLine { x: gaugeRoot.endXG; y: gaugeRoot.yPos }
    }

    // --- Jauge Dynamique ---
    Repeater {
        model: 100
        Item {
            id: consDelegate
            z: 5

            property real myProgress: index / 100.0
            property real segmentVal: myProgress * gaugeRoot.maxInstCons

            // Visibilité restreinte à l'intervalle entre la consommation instantanée et la moyenne
            visible: segmentVal >= Math.min(gaugeRoot.smoothInstCons, gaugeRoot.avgCons) && segmentVal <= Math.max(gaugeRoot.smoothInstCons, gaugeRoot.avgCons)

            // Code couleur : Bleu (inférieur à la moyenne), Orange (supérieur à la moyenne)
            property color fillColor: gaugeRoot.smoothInstCons <= gaugeRoot.avgCons ? Theme.secondary : Theme.main

            PathInterpolator {
                id: consRail;
                progress: consDelegate.myProgress;
                path: instConsPath
            }

            Rectangle {
                width: 22
                height: 3
                x: consRail.x
                y: consRail.y - (height / 2)
                transformOrigin: Item.Left

                // Transformation de perspective
                property real deltaY: gaugeRoot.vanishingPointY - consRail.y
                property real deltaX: gaugeRoot.visualVPX - consRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.05; color: "#FFFFFF" }
                    GradientStop { position: 0.06; color: consDelegate.fillColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }
    }

    // --- Marqueur de Consommation Moyenne ---
    Item {
        z: 15
        PathInterpolator {
            id: avgMarkerRail
            progress: Math.min(gaugeRoot.avgCons / gaugeRoot.maxInstCons, 1.0)
            path: instConsPath
        }

        Rectangle {
            width: 28
            height: 2
            x: avgMarkerRail.x - 4
            y: avgMarkerRail.y - (height / 2) + 5
            transformOrigin: Item.Left

            gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.1; color: Theme.secondary }
                    GradientStop { position: 0.8; color: Theme.secondary }
                    GradientStop { position: 1.0; color: "transparent" }
                }

            property real deltaY: gaugeRoot.vanishingPointY - avgMarkerRail.y
            property real deltaX: gaugeRoot.visualVPX - avgMarkerRail.x
            rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)
        }
    }

    // --- Graduations et Étiquettes ---
    Repeater {
        model: Math.round(gaugeRoot.maxInstCons / gaugeRoot.intervalG) + 1

        Item {
            id: tickInstDelegate
            z: 10

            property int tickVal: index * gaugeRoot.intervalG

            PathInterpolator {
                id: tickInstRail
                progress: tickInstDelegate.tickVal / gaugeRoot.maxInstCons
                path: instConsPath
            }

            Rectangle {
                width: 15
                height: 2
                x: tickInstRail.x -4
                y: tickInstRail.y - (height / 2) + 4
                transformOrigin: Item.Left

                property real deltaY: gaugeRoot.vanishingPointY - tickInstRail.y
                property real deltaX: gaugeRoot.visualVPX - tickInstRail.x
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#FFFFFF" }
                    GradientStop { position: 0.1; color: "#FFFFFF" }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Text {
                text: tickInstDelegate.tickVal
                visible: tickInstDelegate.tickVal !== 0
                color: Theme.textDimmed
                font.pixelSize: 18
                font.bold: true
                font.family: "Arial"
                x: tickInstRail.x - (width / 2)
                y: tickInstRail.y - 34
            }
        }
    }

    // --- Affichage Numérique ---
    Column {
        x: gaugeRoot.endXG + 25
        y: gaugeRoot.yPos - 30
        spacing: 0

        Text {
            text: Math.min(gaugeRoot.smoothInstCons, 99.9).toFixed(1)
            color: Theme.textMain
            font.pixelSize: 18
            font.bold: true
            font.family: "Arial"
            opacity: 0.9
        }

        Text {
            text: "L/100"
            color: Theme.textDimmed
            font.pixelSize: 10
            font.family: "Arial"
        }
    }
}